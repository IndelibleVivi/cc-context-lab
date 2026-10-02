# 官方控制面核对

查阅：2026-10-03。这里记录公开文档的合同，尚未验证任一本机或 VPS build 的实际运行。完整来源表见 [official-docs.json](../references/official-docs.json)。

## 主提示、追加与 snapshot

`--system-prompt-file <file>` 替换默认主提示；`--append-system-prompt-file <file>` 追加。两条路线都有研究价值，对照实验不能混用。主提示替换不会自动处理 tools / messages 中的其他指导。

当前文档说明 system prompt 默认在首个请求记录，resume / continue 可沿用到 compact；`--system-prompt-snapshot off` 用于每个请求重建，要求 v2.1.257+。旧版、bare mode 和 feature-flag 获取条件有版本差异。迭代实验与日常运行应分别选择 snapshot 策略，不能把关闭 snapshot 当作普适优化。

普通子代理的 `--append-subagent-system-prompt` 仅适用于 `-p`，fork 子代理复用会话 prompt。另有 `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` 静态/动态分界（文档标 v2.1.275+）；缓存策略值得后续研究，但并不扩大 context 改写范围。[CLI reference](https://code.claude.com/docs/en/cli-reference)

## 原生来源开关

下面是候选能力表，均以 `1` 启用对应关闭行为。它不是建议一次性打开的配置文件。

| 变量 | 官方描述的控制对象 | 选择时的代价或边界 |
| --- | --- | --- |
| `CLAUDE_CODE_DISABLE_ATTACHMENTS` | attachments | `@文件` 不再展开；技能清单等受影响，不能当作仅清理噪声 |
| `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS` | 内置 commit / PR 指导及 git status snapshot | Git 事实也需另行提供 |
| `CLAUDE_CODE_DISABLE_CLAUDE_MDS` | 各来源 CLAUDE.md 与相关 memory 文件进入 context | 自有身份或项目约束若仍经此入口加载，也会受影响 |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | auto-memory 创建与加载 | 不表示自己的 Memory hooks 一并关闭 |
| `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` | 随 CC 分发的 skills / workflows | 用户与插件 skills 保留；部分内置命令可手动调用但不呈给模型 |
| `CLAUDE_CODE_DISABLE_CFC_PROMPT` | Chrome 指导章节和 bundled skill | 浏览器工具仍在；文档标 v2.1.257+ |

来源：[Environment variables](https://code.claude.com/docs/en/env-vars)。其余变量不要根据名称猜最早支持版本，未来以目标安装验证。

官方 SDK 文档还明确：Git workflow 指导位于 Bash description；附件关闭后，可用 subagents 清单和后台任务通知仍可能进入。SDK message stream 不完整呈现 system reminders，终端没有显示不能证明请求里没有。[Modifying system prompts](https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts#context-claude-code-adds-outside-the-system-prompt)

## Mods

官方 changelog 将 Claude Mods 列于 2.1.287（2026-10-01）。当前 reference 也以该版为描述基线；最终字段以目标 build 生成的 TypeScript declarations 为准，GitHub 上的类型可能滞后。[Changelog](https://code.claude.com/docs/en/changelog)、[Mods reference](https://code.claude.com/docs/en/plugins/mods/reference)

| 事件 | 当前文档承诺 | 不能据此推导 |
| --- | --- | --- |
| `prompt.section` | 按具名 section 改正文或省略 | 所有动态提醒都属于 section |
| `prompt.compose` | 处理 `{ id, text, scope }` sections | 已接管 tools、历史 messages |
| `prompt.context` | 每个 conversation 初始 context blocks | 后续每次 nested instruction 加载均有事件 |
| `prompt.attachment` | 按 type 处理提醒，部分类型有 detail | 所有正文都已分离出原始材料 |
| `tool.describe` | 改工具 description | 参数 schema、权限或工具实现跟着改变 |
| `skill.prompt` | 处理展开给模型的 skill 正文 | 已解决 skill discovery 或版本兼容 |
| `session.compact` | 压缩前介入，可返回 skip | 全量 / 局部 compact 模板都能替换 |

`next.origin` 描述发起事件的 plugin/tier；特定事件自身的 `origin` 字段有其独立语义，不能只凭同名就混用。对每种事件读目标 build 类型。[Mods reference](https://code.claude.com/docs/en/plugins/mods/reference)

Mods 可因配置、远程开关或 handler 错误而不执行，CC 会话仍可能继续。因此区分“配置存在、该进程加载、事件命中、最终 request 改变”。如果自有 profile 依赖清理层，缺失时应如实显示未生效，不绕过上游或管理员限制。[Troubleshooting](https://code.claude.com/docs/en/plugins/mods/troubleshoot)

官方 `claude plugin test` 支持无模型、无登录、无网络的事件 stub 测试；可用于自己写出的 Mods fixture。测试命令仍会加载被测模块，所以先读 module，再在隔离目录执行。当前 repo 尚未运行该命令。[Test a mod](https://code.claude.com/docs/en/plugins/mods/test)

## 为什么暂不把 bare 作为默认研究基线

`--bare` 同时改变配置发现、OAuth/keychain 读取、MCP、后台任务与 reminders。文档标明 2.1.286 前后行为不同；它适合另设独立实验，不能与“只替换指导文字”的组混在一起。[Headless / bare mode](https://code.claude.com/docs/en/headless#start-faster-with-bare-mode)

## 实际输入怎么观察

文档支持 `OTEL_LOG_RAW_API_BODIES=file:<dir>` 保存未被日志长度截断的 request / response；request 中检查 system、messages、tools，`query_source` 区分 compact 等来源。Extended thinking 仍会被 redacted；文件并不等于完整内部状态。此变量在 project/local settings 中被忽略，不能只把它写进项目 settings 就宣称完成采集。Exporter 与 telemetry 启用条件仍需按目标 build 的隔离配置验证。[Monitoring](https://code.claude.com/docs/en/monitoring-usage#api-request-body-event)

采集会包含完整对话与工具结果。未来仅用合成材料、私有本地目录做获授权实验；这次未启用采集、代理或真实模型调用。方案与验收见 [experiments](../experiments/README.md)。
