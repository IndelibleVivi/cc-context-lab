# Claude Code Context Lab

[中文 (canonical documentation)](README.md) · [English](README.en.md)

Understand where Claude Code context comes from, how it is assembled and how it changes across turns and resumed sessions. **Handbook, Workbench and Toolkit** connect explanations with fixed, reproducible material. The repository slug remains `cc-context-lab`. Other harnesses are comparative references; reusable wire readers do not constitute non-CC product support.

The CC research scope includes a complete owned core, ambient/present state, automatic memory recall, autonomous turns, channel inputs and compact/resume continuity. Fewer tokens do not automatically mean better interaction.

## Three ways to start

| Goal | Start here |
| --- | --- |
| Learn mechanisms and change methods | [Handbook](docs/handbook/index.md): owned core, dynamic state and compact/resume |
| Reproduce a synthetic example | Run the command below and inspect requirements, original values, failures and evidence gaps in Workbench |
| Inspect an explicitly selected CC run | [CC runs](docs/cc-runs.md): selection → captures/sidecar → single request or explicit pair → frozen snapshot |

Requires Python 3.10+ and Node.js. Reading alone requires no dependency installation.

```sh
python3 scripts/build_context_atlas.py --recipe owned-core --out .cache/cc-context-workbench
```

Open `index.html` in the output directory. The three recipes use fixed synthetic material, including satisfied structural checks, intentional FAIL examples and unassessed requirements. They are not installed configurations. Existing Toolkit scripts run cases, studies, request inspection and explicit CC imports; Workbench presents the same canonical results. See [Workbench usage](workbench/README.md).

## Evidence and boundaries

Synthetic structural checks, public source inspection, offline checks against a specified native build, actual requests and model behavior are separate evidence layers. Recipe native protocols are `NOT_EXECUTED`; actual lifecycle and behavior remain `NOT_ASSESSED`. Historical native results retain their original dates, versions and scope. See [current state](docs/current-state.md) and [historical research evidence](docs/research-evidence.md).

Lab does not discover private logs, follow paths or URLs in captures, install candidates, start schedulers, call models or send messages. Private captures enter local views only through explicit input. Outputs must be outside Git or in ignored, untracked worktree paths. Actual requests, identities, configuration, transcripts and private continuity must remain outside Git, including private remotes. External Memory/state, production integration and recovery remain with the original runtime owner.

The [architecture diagram](README.md#架构与边界) distinguishes local evidence paths from separately authorized runtime integration. A request alone cannot establish origin or lifecycle: unknown stays unknown. Unobserved partial-capture fields are not empty or deleted. Different wire formats are not automatically paired.

## Documentation map

| Content | Entry |
| --- | --- |
| Three complete offline learning paths | [Handbook](docs/handbook/index.md) |
| Local views, fixed inputs, comparisons and exports | [Workbench](workbench/README.md), [Context cases](docs/context-cases.md), [CC runs](docs/cc-runs.md) |
| Sources, controls and version evidence | [Context map](docs/context-map.md), [Official controls](docs/official-controls.md), [Upstreams](docs/upstreams.md) |
| Personalization and autonomous turns | [Companion context](docs/companion-context.md), [Continuity and Memory](docs/continuity-and-memory.md) |
| Experiments, integration and upgrades | [Experiments](experiments/README.md), [Runtime integration](docs/runtime-integration.md), [Maintenance](docs/maintenance.md) |
| Current status and remaining gates | [Current state](docs/current-state.md), [Programme](docs/development-programme.md) |

Run `python3 scripts/check_offline.py` after authored source changes. This gate does not execute official binaries, network checks, runtime probes or models. Native checks and actual observations have separate preconditions; offline success does not establish installation, deployment or interaction quality.

Original functional material uses [SUL-1.0](LICENSE); original documentation, diagrams and research composition use [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md). Third-party material retains its original rights. This is layered source-available licensing, not a repository-wide OSI open-source license. Plugin directory copies must carry the applicable license files. See [LICENSING](LICENSING.md) and the [agent contract](AGENTS.md).
