#!/usr/bin/env python3
"""Reproduce a reviewed tutorial pruner's claims on temporary synthetic JSONL.

Pass the original Markdown tutorial (including its Python code fence), not a
real transcript. The source is executed: inspect it first. No real CC process,
settings, sentinel or transcript is used. Exit 0 means observations reproduced,
not that the pruner is safe or effective in a live session.
"""
import argparse
import builtins
import json
from pathlib import Path
import re
import tempfile
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    blocks = re.findall(r'^```python\n(.*?)^```', args.source.read_text(), re.M | re.S)
    if len(blocks) != 1:
        parser.error('expected one reviewed Python code fence')
    scope = {'__name__':'reviewed_tutorial_fixture'}
    exec(compile(blocks[0], '<reviewed tutorial>', 'exec'), scope)
    observations = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        scope.update(MARKERS=('<LAB_DYNAMIC>',), SENTINEL=str(root/'enabled'),
                     BACKUP_DIR=str(root/'backups'))
        def attachment(uid, content, parent='user-1'):
            return {'type':'attachment', 'uuid':uid, 'parentUuid':parent,
                    'attachment':{'type':'hook_additional_context', 'content':content}}
        def exercise(name, rows):
            path = root/(name+'.jsonl')
            raw = '\n'.join(json.dumps(r) if isinstance(r,dict) else r for r in rows)+'\n'
            path.write_text(raw)
            scope['_prune'](str(path))
            return path, raw, path.read_text().splitlines()

        assert scope['_enabled']('lab-session') is False
        observations.append('B01 absent sentinel disables; no real sentinel used')
        Path(scope['SENTINEL']).write_text('different-session')
        with patch.dict(scope, {'open':lambda *a, **k: (_ for _ in ()).throw(OSError('synthetic read failure'))}):
            assert scope['_enabled']('lab-session') is True
        observations.append('B02 unreadable existing sentinel enables even a non-allowlisted session')

        rows=[attachment('old',['<LAB_DYNAMIC> old']), attachment('latest',['<LAB_DYNAMIC> latest'],'old')]
        path, original, lines=exercise('all-existing',rows)
        after=[json.loads(line) for line in lines]
        assert all(r['attachment']['content']==[''] for r in after)
        assert [(r['uuid'],r['parentUuid']) for r in after]==[(r['uuid'],r['parentUuid']) for r in rows]
        assert any(p.read_text()==original for p in (root/'backups').iterdir())
        observations.append('B03 all existing marked entries are cleared, including latest; chain fields and backup preserved')

        _,_,lines=exercise('quoted-user',[{'type':'user','uuid':'u','message':{'content':'quoted <LAB_DYNAMIC>'}},attachment('foreign',['OTHER'])])
        assert [json.loads(line) for line in lines]==[{'type':'user','uuid':'u','message':{'content':'quoted <LAB_DYNAMIC>'}},attachment('foreign',['OTHER'])]
        observations.append('B04 user quotation and unmarked attachment remain unchanged')

        _,_,lines=exercise('mixed',[attachment('mixed',['<LAB_DYNAMIC> old','UNRELATED_PAYLOAD'])])
        assert json.loads(lines[0])['attachment']['content']==['']
        observations.append('B05 marker in first list item clears the entire content array, including unrelated later payload')

        row=attachment('second',['FIRST_UNMARKED','<LAB_DYNAMIC> second'])
        _,_,lines=exercise('second',[row])
        assert json.loads(lines[0])==row
        observations.append('B06 marker only in second list item is not selected')

        _,_,lines=exercise('malformed',['not-json',attachment('marked',['<LAB_DYNAMIC> value'])])
        assert lines[0]=='not-json'
        observations.append('B07 unparseable line preserved during a matched rewrite')

        # Simulate a write that changes the file, then raises before truncate.
        failure=root/'write-failure.jsonl'
        original=json.dumps(attachment('failure',['<LAB_DYNAMIC> '+'x'*1000]))+'\n'
        failure.write_text(original)
        class InterruptedWrite:
            def __init__(self, handle): self.handle=handle
            def __enter__(self): return self
            def __exit__(self,*a): return self.handle.__exit__(*a)
            def __getattr__(self,name): return getattr(self.handle,name)
            def write(self,body):
                self.handle.write(body); self.handle.flush()
                raise OSError('synthetic interruption before truncate')
        def fault_open(path,mode='r',*a,**k):
            handle=builtins.open(path,mode,*a,**k)
            return InterruptedWrite(handle) if str(path)==str(failure) and mode=='r+' else handle
        with patch.dict(scope,{'open':fault_open}):
            try: scope['_prune'](str(failure))
            except OSError: pass
            else: raise AssertionError('expected injected write error')
        assert failure.read_text()!=original
        try: json.loads(failure.read_text())
        except json.JSONDecodeError: pass
        else: raise AssertionError('expected invalid JSONL row after interrupted rewrite')
        assert any(p.read_text()==original for p in (root/'backups').iterdir())
        observations.append('B08 write error can leave changed invalid JSONL; backup exists but no automatic rollback')
    print(json.dumps({'observations':observations,'passed':len(observations),
                      'live_request_effect':'not_tested','production_files_touched':False},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
