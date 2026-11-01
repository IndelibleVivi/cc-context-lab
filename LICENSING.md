# Licensing map / 授权范围

This repository uses two licenses for different materials. They are **not a
choice of license for the same file**. The grants cover only project-original
material and rights that its respective authors can grant.

Copyright © 2026 Faye Fang for project-original material. Contributors retain
copyright in their own contributions; this map does not assign their rights.

## Current path map

| Material | Paths / rule | License |
| --- | --- | --- |
| Functional source, tools, tests and browser implementation | `*.py`, `*.js`, `*.mjs`, `*.cjs`, `*.ts`, `*.css`, `*.html` under `context_lab/`, `scripts/`, `experiments/` and `workbench/`; `.gitignore` | [SUL-1.0](LICENSE) |
| Machine-executed experiment inputs and plugin configuration | All `experiments/**/*.json` and `experiments/**/*.jsonl`, including `experiments/continuity-cases.json`, decision cases, synthetic fixtures, `hooks/hooks.json`, and both `experiments/context-profile/.claude-plugin/plugin.json` and `experiments/daily-quiet/.claude-plugin/plugin.json` | [SUL-1.0](LICENSE) |
| Documentation, research prose and diagrams | Root Markdown files, `docs/**/*.md`, `experiments/**/*.md`, `workbench/README.md`, including diagrams authored in those documents | [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md) |
| Research indexes and Atlas relationship model | Original selection, arrangement and analysis in `references/**/*.json` and `workbench/model.json` | [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md) |
| Original executable examples embedded in documentation | Functional code and shell examples within the documentation above | [SUL-1.0](LICENSE); surrounding prose remains CC BY-NC-SA 4.0 |
| License texts and notices | `LICENSE`, `LICENSE-DOCUMENTATION.md`, `LICENSING.md` | The SUL text is reproduced unchanged from SPDX; the documentation notice and this map use CC BY-NC-SA 4.0. The standard licenses retain their own terms |

Patterns include nested paths and hidden `.claude-plugin/` directories. The
third-party exclusions below take priority over the path map. Add an explicit
classification when introducing a new type of material.

The plugin manifests use `SUL-1.0 AND CC-BY-NC-SA-4.0` to identify the two
licenses present in each mixed code/documentation directory. This aggregate
metadata does not apply both licenses to every file; the path map controls.
When copying a plugin directory on its own, also carry `LICENSE`,
`LICENSE-DOCUMENTATION.md` and this map so recipients receive the terms.

## Meaning and authoritative terms

**SUL-1.0 is source-available, with use restrictions.** It permits personal,
noncommercial and internal business use. Distribution or provision to others
must be free of charge and noncommercial, with the license and required
notices retained. Modified copies must prominently indicate modification.
See the complete [SUL-1.0 text](LICENSE) and its
[SPDX entry](https://spdx.org/licenses/SUL-1.0.html). Do not describe the
software as OSI open source.

**CC BY-NC-SA 4.0** grants reuse of the mapped original content under its
attribution, NonCommercial and applicable ShareAlike conditions. See the
[documentation notice](LICENSE-DOCUMENTATION.md) and
[canonical legal code](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en).
These summaries do not add conditions to, or replace, the standard licenses.

## Third-party and private boundaries

Third-party names, identifiers, source facts, short quotations and attributed
source material in research files remain subject to their original rights,
licenses and applicable exceptions. The CC grant covers our original research
expression and arrangement, not ownership of those third-party elements or
exclusive rights over facts.

Some experiment scripts read and execute selected functions from an external
checkout supplied by the operator. That checkout, and any upstream content
temporarily loaded or generated during a run, retains its original license.
The SUL grant for our loader and assertions does not relicense upstream code.
Source links and revisions are recorded in `references/` and the relevant
guides. This repository does not distribute the complete upstream
implementations or native prompt texts; Daily quiet stores reviewed native
fragment digests and project-authored replacements.

No rights in third-party trademarks or endorsement are granted. Private
identity, account configuration, chats, real captures, transcripts and
continuity are outside this repository and outside these grants.

## Revision boundary

This licensing decision was adopted on **2026-11-01**. Revisions through
`563b1625b724c9b09ba327e0a1a3394fab87cf55` did not include a public license
notice. These grants accompany the current project-original material; they
do not remove any permissions previously granted by a relevant rights holder.
Historical source snapshots retain their own notices and evidence dates.

## 中文说明

本仓库按材料分层授权：原创功能代码、脚本、测试、网页实现、机器执行的合成输入与
插件配置使用 **SUL-1.0**；原创研究文字、文档、图示，以及资料索引中的原创编排和分析
使用 **CC BY-NC-SA 4.0**。文档内可执行代码示例仍归 SUL。两种许可分别适用于上表所列
材料，不是同一文件可任选一种的双重许可。

第三方引文、源码标识符、事实与外部 checkout 保留原有权利；运行本仓库的实验不会
改变它们的许可。私人身份、会话和真实请求不在公开内容及授权范围内。SUL 是带用途
限制的 source-available 许可，不称为 OSI open source。具体条件、免责与适用边界以
对应标准许可正文为准。
