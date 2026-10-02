# CC Context Lab

研究、比较和维护 Claude Code 的 harness 指导与 context 装配方式。`cc-context-lab` 是工作名，正式名称待定。

目前作为 private 研究仓库维护：[GitHub](https://github.com/IndelibleVivi/cc-context-lab)。

目标是让 CC 继续提供工具执行、会话和 MCP 能力，同时理解并逐步掌握送给模型的主提示、工具说明、动态 reminders、文件与记忆来源，以及 compact / resume / subagent 的继承方式。自己的 core 可以充分而完整；研究重点是控制来源、冲突与生命周期，不能把 token 更少直接当成体验更好。

目前交付是**有出处的研究库和实验设计**，尚未提供可安装的 context manager、可直接部署的 persona/profile 或经真实请求验证的完整剥离方案。当前证据与覆盖范围见 [current state](docs/current-state.md)。

## 从这里读

| 你要做什么 | 入口 |
| --- | --- |
| 理解默认指导究竟从哪里进入 | [Context map](docs/context-map.md) |
| 查官方 CLI、开关与 Mods 的实际边界 | [Official controls](docs/official-controls.md) |
| 对照已有仓库，决定复用什么 | [Upstream dossiers](docs/upstreams.md) |
| 设计自己的完整 context profile | [Profile design](docs/profile-design.md) |
| 设计能反驳假设的对照实验 | [Experiments](experiments/README.md) |
| 为已有受管 runtime 准备配置改动 | [Runtime integration](docs/runtime-integration.md) |
| 持续更新来源、版本与结论 | [Maintenance](docs/maintenance.md) |

建议先读 context map，再把 official controls 与 upstream dossiers 并排看。它们分别回答“当前官方接口承诺什么”和“这些项目实际实现了什么”。

## 使用方式与边界

纯阅读无需安装依赖。用 `python3 scripts/check_upstreams.py` 可只读检查七个公开上游是否更新，需要 Python 3.10+ 和 Git；详细退出码见 [maintenance](docs/maintenance.md)。版本与覆盖声明都带观察日期；上游 source inspection、离线测试、真实 request 和行为结果分别记录。研究里出现的配置命令是实验候选，不会由本仓库自动执行。

已有一份可重跑的 [roof-mod 合成缺陷复现](experiments/README.md)，需要 Node.js 与已阅读的 exact upstream checkout；不启动 Claude Code。

对已有 runtime 的修改继续由其 source repo、candidate renderer 和 operator runbook 管理。本仓库准备可审核的规则、证据和接入说明，不持有生产配置 authority。当前阶段是本地研究，未连接或修改 VPS。

仓库内容面向后续维护者，保留原创技术归纳和公开 source links。私人讨论原文、身份正文、账号配置、真实请求、transcripts 和机器映射放在 Git 外；`.cache/`、`.local/`、`artifacts/` 等仅作本机缓存。第三方代码与原厂提示全文不 vendoring。本仓库未公开发布，也未选择公开 license。

维护约定见 [AGENTS.md](AGENTS.md)。
