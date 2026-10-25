#!/usr/bin/env python3
"""Inspect target-generated Mods types and real engine composition without a model.

Runs a local slash-command session with an explicit synthetic key and a loopback
endpoint that rejects every request. It does not install a plugin or use a real
provider. Read the candidate before executing. This is not an OS sandbox.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
PROBE_MODULE = '''const names = [];
let resolved;
export function register(on) {
  on('session.start', async ($, e, next) => {
    await $.command.register({name:'lab-inspect', description:'Inspect section metadata locally'});
    return next(e);
  });
  on('prompt.section', ($, e, next) => {
    names.push({name:e.name, omitted:e.text===null, length:e.text===null ? 0 : e.text.length});
    return next(e);
  });
  on('prompt.compose', ($, e, next) => {
    resolved = {model:e.model, promptModel:e.promptModel, traits:e.traits, tools:e.tools, surfaces:e.surfaces};
    return next(e);
  });
  on('command.run', {command:'lab-inspect'}, async ($) => {
    const result = await $.prompt.compose();
    return {text:JSON.stringify({kind:'lab-section-probe',resolved,names,sections:result.sections.map(s=>({id:s.id,scope:s.scope,length:s.text.length}))})};
  });
}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--claude', required=True, help='trusted target executable')
    parser.add_argument('--candidate', type=Path, default=ROOT/'experiments/context-profile')
    parser.add_argument('--output', type=Path, default=ROOT/'.cache/context-runtime-probes')
    args = parser.parse_args()
    executable = shutil.which(args.claude)
    if not executable:
        parser.error('Claude executable not found')
    source = args.candidate.resolve()
    output = args.output.resolve()
    if not (source/'.claude-plugin/plugin.json').is_file():
        parser.error('candidate must have a plugin manifest')
    if output == source or source in output.parents:
        parser.error('output must be outside candidate source')
    output.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=output))
    probe = run/'probe'
    (probe/'.claude-plugin').mkdir(parents=True)
    (probe/'hooks').mkdir()
    (run/'config').mkdir()
    candidate = run/'candidate'

    def ignore(directory, names):
        ignored = set(names) & {'.git', 'node_modules', '__pycache__'}
        if Path(directory) == source/'.claude-plugin': ignored.add('types')
        return ignored

    shutil.copytree(source, candidate, ignore=ignore)
    (probe/'.claude-plugin/plugin.json').write_text(json.dumps({
        'name':'lab-section-probe', 'version':'0.0.0',
        'description':'Local section metadata inspector', 'author':{'name':'CC Context Lab'}}))
    (probe/'hooks/hooks.json').write_text(json.dumps({'modules':['./register.js']}))
    (probe/'hooks/register.js').write_text(PROBE_MODULE)
    requests = []

    class Reject(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('content-length', 0)))
            requests.append({'method':'POST', 'path':self.path, 'bytes':len(body)})
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"type":"error","error":{"type":"invalid_request_error","message":"Lab rejects model requests"}}')

        def do_GET(self):
            requests.append({'method':'GET', 'path':self.path})
            self.send_response(404)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Reject)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = {'PATH':os.environ.get('PATH', os.defpath), 'LANG':'en_US.UTF-8',
           'CLAUDE_CONFIG_DIR':str(run/'config'), 'DISABLE_AUTOUPDATER':'1',
           'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC':'1',
           'CLAUDE_CODE_DISABLE_CLAUDE_MDS':'1', 'CLAUDE_CODE_DISABLE_AUTO_MEMORY':'1',
           'CLAUDE_CODE_DISABLE_BUNDLED_SKILLS':'1',
           'ANTHROPIC_BASE_URL':f'http://127.0.0.1:{server.server_port}',
           'ANTHROPIC_API_KEY':'cc-context-lab-synthetic-key'}
    command = [str(Path(executable).resolve()), '-p', '/lab-inspect',
               '--plugin-dir', str(probe), '--plugin-dir', str(candidate),
               '--setting-sources', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
               '--tools', '', '--no-chrome', '--no-session-persistence', '--permission-mode', 'dontAsk']
    report = {'schema':'cc-context-lab.runtime-probe/1',
              'started_at':datetime.now(timezone.utc).isoformat(), 'command':command,
              'status':'not_observed', 'model_behavior':'not_tested',
              'scope':'local slash command; real engine composition; source metadata only',
              'settings':{'claude_mds':False,'auto_memory':False,'bundled_skills':False,
                          'tools':[],'mcp_servers':[],'session_persistence':False}}
    try:
        version = subprocess.run([command[0], '--version'], cwd=run, env=env,
                                 capture_output=True, text=True, timeout=45)
        report['version_output'] = version.stdout.strip()
        result = subprocess.run(command, cwd=run, env=env, capture_output=True, text=True, timeout=45)
        report.update(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith('lab-section-probe: '):
                report['observation'] = json.loads(line.removeprefix('lab-section-probe: '))
        declarations = sorted(probe.glob('.claude-plugin/types/*/index.d.ts'))
        report['generated_types'] = [{'file':str(p.relative_to(run)),
                                      'header':p.read_text().splitlines()[0]} for p in declarations]
        expected_header = '// Written by Claude Code ' + version.stdout.split(' (Claude Code)')[0].strip() + '.'
        header_ok = any(t['file'].endswith('/claude-code/index.d.ts') and t['header']==expected_header for t in report['generated_types'])
        observation = report.get('observation', {})
        has_core = any(s['id']=='lab:core' and s['scope']=='session' for s in observation.get('sections', []))
        if result.returncode == 0 and observation.get('kind')=='lab-section-probe' and observation.get('names') and header_ok and has_core and not requests:
            report['status'] = 'observed'
    except (subprocess.TimeoutExpired, OSError, ValueError) as error:
        report['error'] = f'{type(error).__name__}: {error}'
    finally:
        server.shutdown()
        server.server_close()
    report['requests_to_local_sink'] = requests
    report_path = run/'report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status':report['status'], 'version':report.get('version_output'),
                      'section_events':len(report.get('observation', {}).get('names', [])),
                      'local_sink_requests':len(requests), 'report':str(report_path)}, ensure_ascii=False))
    return 0 if report['status']=='observed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
