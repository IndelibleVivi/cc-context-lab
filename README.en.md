# Harness Context Engineering Lab

[中文 (canonical documentation)](README.md) · [English](README.en.md)

Research, compare and maintain the sources, assembly and lifecycle of context in agent harnesses. Claude Code is the most deeply studied harness; the existing repository slug remains `cc-context-lab`. Long-running companion interaction is a primary use case, including an owned core, present context, automatic memory recall, autonomous turns, channels and continuity. Fewer tokens are not a substitute for better interaction.

The repository currently provides a sourced research library, Context Atlas, reproducible synthetic A/B studies, local request observation, multi-stage context cases and CC-specific source candidates. The [project repository](https://github.com/IndelibleVivi/cc-context-lab) uses SUL-1.0 for original functional material and CC BY-NC-SA 4.0 for original research content; see the [licensing map](LICENSING.md). It is not a deployed context manager, complete persona/profile or fully verified context-stripping solution. See the [current evidence and gaps](docs/current-state.md).

## Run the daily quiet comparison

Requires Python 3.10+ and Node.js. No dependency installation, network or model call is needed:

```sh
node --test experiments/daily-quiet/tests/rules.test.mjs
mkdir -p .cache/daily-quiet
node experiments/daily-quiet/demo.mjs > .cache/daily-quiet/input.json
python3 scripts/run_context_case.py .cache/daily-quiet/input.json --out .cache/daily-quiet/result
python3 scripts/build_context_atlas.py --case .cache/daily-quiet/result/case.json
```

The [Daily quiet experiment](experiments/daily-quiet/README.md) supplies portable pure rules, a thin opt-in Mods entry, native test-kit fixtures and a synthetic case. Reviewed engine prose is identified by fragment digests; unknown text, new facts and tool schemas survive. There is no binary-version gate for presentation filtering. Exact recovery and authorization stay with each runtime owner.

The case exercises baseline, candidate, changed native text and a partial system/tools-only shape. Seven structural requirements pass; four requirements remain `NOT_ASSESSED`, including unknown history, resume, model behavior and delivery. Linux CC 2.1.314 and 2.1.316 passed three synthetic native event tests each; validation passed with catalog warnings. These results do not establish complete provider requests or conversation quality. See [portable evidence](references/daily-quiet.json).

## Inspect, compare and prepare a change

| Reader goal | Entry |
| --- | --- |
| Understand source, trust and runtime-owner boundaries | [Chinese README architecture](README.md#架构与边界), [Context DevOps](docs/context-devops.md) |
| Reproduce multi-stage context checks | [Context cases](docs/context-cases.md) |
| Inspect explicit Anthropic Messages / OpenAI Responses captures | [Request observation](docs/request-observation.md) |
| Browse sources, cases, comparisons and fixed change briefs | [Context Atlas](workbench/README.md) |
| Compare current/history, placement and source selection | [Context studies](experiments/companion-input/STUDIES.md) |
| Study companion context, autonomous turns and continuity | [Companion context](docs/companion-context.md), [development programme](docs/development-programme.md) |
| Check CC-specific source candidates and target evidence | [Maintenance](docs/maintenance.md), [target runtime](docs/target-runtime.md) |
| Trace sources and dated coverage | [Context map](docs/context-map.md), [research evidence](docs/research-evidence.md), [upstreams](docs/upstreams.md) |

The observer preserves explicit request values and unknown parameters. The wire format does not imply support for every harness using it. Same-format comparisons align JSON pointers; cross-format comparisons do not infer semantic equivalence. Origin and lifecycle remain `unknown`. Partial captures must declare the observed top-level fields; unobserved history is unknown rather than empty, absent or deleted. Unexpanded server-side references remain gaps. Imported manifests are declarations, not independently verified runtime provenance.

Build the default synthetic Atlas with `python3 scripts/build_context_atlas.py`. Import real local captures only through explicit `--capture` inputs and keep generated output outside Git or in ignored paths. The builder does not discover logs or follow external references. Its downloadable brief prepares evidence; it grants no installation, deployment or messaging authority.

## Verification and operational boundary

Run the authored offline gate from the repository root:

```sh
python3 scripts/check_offline.py
```

It checks the engines, CLI, presenters, synthetic candidates and request preparation without downloading dependencies, executing a CC binary, contacting upstreams or calling models. [Upstream checks](docs/maintenance.md), native plugin checks, local composition probes and real model experiments remain separate operations with their own prerequisites. The default case deliberately includes a structural failure; its runner exits 1 and still writes the report. The Daily quiet case above exits 0 with explicit unassessed requirements.

Runtime source repositories, candidate renderers and operator runbooks own real configuration, installation, recovery and delivery. Lab code does not automatically modify deployments, start schedulers, call models or send messages. A managed consumer's installed state is separate from Lab's synthetic results. See [runtime integration](docs/runtime-integration.md).

## Privacy, provenance and rights

The repository contains project-authored research, transformations, synthetic fixtures and public source links. It does not vendor complete third-party implementations or native prompt texts. Private discussions, identity, account configuration, real requests, transcripts, machine mappings and continuity remain outside Git, including private remotes. `.cache/`, `.local/` and `artifacts/` are local-only output locations.

Original code, scripts, tests and executable experiment materials use [SUL-1.0](LICENSE), a source-available license with use restrictions. Original documentation, diagrams and research arrangement use [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md). Third-party sources and externally loaded checkouts retain their original rights. This is not a single OSI open-source grant for the whole repository. Include the applicable notices and [path map](LICENSING.md) when copying a plugin directory. [AGENTS.md](AGENTS.md) records maintenance authority and verification rules; the Chinese README is the canonical full documentation map.
