# 目标 build：类型与实际 composition

观察日期：2026-10-05。已用官方 **Claude Code 2.1.289**（darwin-arm64 portable artifact）启动一个隔离的**本地命令会话**，生成目标 types，并调用真实 engine 的 `$.prompt.compose()`。没有取得模型回答，也没有验证完整 request body；原始结果留本地，便携证据见 [target-runtime-2.1.289.json](../references/target-runtime-2.1.289.json)。

## 怎样复跑

```sh
python3 scripts/probe_context_runtime.py --claude '<trusted-claude-executable>'
```

[探针](../scripts/probe_context_runtime.py) 在 `.cache/context-runtime-probes/run-*/` 中复制已审阅 candidate、写入仅用于检查的 mod，以 `--plugin-dir` 加载两者。它注册 `/lab-inspect`，本地 handler 调用 composition API，返回 section 的 **name/id、scope、是否省略和字符长度**，不返回原厂或私人提示正文。CLI 返回后保留 JSON 报告与 engine 自动生成的 `.d.ts`。

该脚本与 [官方 offline 检查](maintenance.md#检查指定-cc-版本的-candidate) 分开：后者验证 manifest/合成事件链；这个入口实际启动本地命令会话。它不安装插件、不改日常 config、不保存可 resume 的会话，也不调用真实 provider。需要明确选择可信 binary 与已审阅 candidate。

运行条件：独立 `CLAUDE_CONFIG_DIR`、空 settings sources、空 MCP/tools、关闭 Chrome/CLAUDE.md/auto-memory/bundled skills、`dontAsk` 和 `--no-session-persistence`。认证值为公开合成字符串，`ANTHROPIC_BASE_URL` 指向临时 loopback HTTP server；任何到达它的请求都被拒绝，正文不落盘。本次端点收到 **0 个请求**。这不是 OS 网络隔离或对任意 mod 的安全保证，不能据此说已做完整抓包。

脚本的成功条件同时包含：命令返回结构化观察、收到 section 事件、真实 composition 含 session scope 的 `lab:core`、生成类型 header 与目标 `--version` 一致，以及 loopback 请求数为零。失败留报告、返回 1；不会改用真实 provider 补测。`--candidate` / `--output` 可选择已审阅目录与本地输出路径，输出仍应留 Git 外。

官方说明 `--plugin-dir` 为当前会话加载 mod 而不安装，目录加载/重载时生成类型；`$.prompt.compose()` 是可在本地命令中调用的 API。[Create a mod](https://code.claude.com/docs/en/plugins/mods/create#get-type-definitions-for-your-version)、[Mods API](https://code.claude.com/docs/en/plugins/mods/api)

## 这次实际看到了什么

目标生成了三份声明：`claude-code/index.d.ts`、`claude-code-tools/index.d.ts`、`claude-code-mcp/index.d.ts`。核心声明 header 明确为 **2.1.289**。官方 test kit 未生成 types 的旧记录仍然成立；独立的本地命令加载补足了这一层证据。

本次 engine 解析出的 model/promptModel 都为 `claude-opus-5-5`，traits 为 `lean / print / skills`，tools/surfaces 为空。model 字符串只是本地 prompt 分支的选择结果，不代表调用或访问了该模型；关闭 bundled skills 也没有消除 `skills` trait，不能把它与该环境变量当作同一个开关。

收到 **23 个 `prompt.section` 事件**（含正文为 null 的省略项）；最终 composition **9 段**：

| 顺序 | composition id | scope |
| --- | --- | --- |
| 1 | `lean_body` | shared |
| 2 | `lab:core` | session |
| 3 | `communication` | session |
| 4 | `pronouns` | session |
| 5 | `action_caution` | session |
| 6 | `env_info_simple` | session |
| 7 | `context_management` | session |
| 8 | `act_dont_rederive` | session |
| 9 | `total_tokens` | session |

这证明 candidate 的 core 在真实 engine composition 中处于 shared/session 边界。`memory` 在本次关闭来源后是一个 null 事件，未进入最终列表。完整事件名及长度在 JSON 中；长度为 JavaScript string length，不是 tokens。

**事件名列表不等于最终 composition 列表。** 例如本次 `lean_body` 和 `total_tokens` 出现在组合结果，但没有对应的 section 事件观察。`name` 与 `id` 是不同 API 字段；已观察的部分 engine 段共用同一个名字，但不能假定每个组合段都经过 `prompt.section`，更不能从静态提取文件名直接猜 matcher。

这里只核元数据，不凭名称把任何正文判定为“可以删除的静态指导”；candidate 默认仍选中 **0 个 engine section**。其它 model、interactive、工具集合、policy 与来源组合须各留版本化证据。

## 目标类型带来的修订

已阅读的具体 symbols 列在 JSON；没有审阅完整声明或运行 TypeScript compiler。

| 面 | 2.1.289 生成声明的结论 | 仍需验证 |
| --- | --- | --- |
| `prompt.compose` / `prompt.section` | 保持 sections/id/text/scope 与 name/text 形状；本轮实际观察到 engine 调用 | 其他分支与实际 HTTP request |
| `prompt.attachment.detail` | 从旧公开 types 的“没有字段”推进为 type-discriminated union；仅声明 `plan_mode`、`plan_mode_reentry`、`plan_mode_exit` | 哪些真实事件带 detail；其它载荷仍不能编造结构 |
| 三类 plan detail | full/sparse、planFilePath、hasPlan 按类型分配；detail 可缺省，字段 pinned | host 自有 plan instructions 仍只在 text 中，不能仅保留 detail 就重建全部正文 |
| 未声明的 attachment | detail key 缺省；新增该 key 的 rewrite 会被拒绝 | 不能给 todo/hook/channel 自造 `detail.tasks` 等字段 |
| `tool.describe` | input `isDeferred?: true`；result `isDeferred?: boolean`，省略时保留 engine placement | 真实工具发现路径。本 candidate 仍只改 description |
| `session.compact` | trigger/agentId/instructions/messages，输出压缩后 messages 或 skip；handle 保真语义仍声明 | compact 未执行；局部 summarize、precompute、重载和每个内部模板未覆盖 |
| `turn.step` | model/effort 可改；messageCount pinned，没有 rewritable messages 字段 | 不是通用 request history 过滤接口 |
| `prompt.submit` | hook 可在 `next` 前附加 `context` blocks，置于原话之后；大载荷可能文件化；asUser 不改变 plugin origin | 实际输入包装、自动召回交付与历史保留未测 |
| `clock.after/every` | 目标声明有 timer 接口；官方文档区分后台 callback 与 submit turn | 没有运行 timer、heartbeat 或 scheduler |

`prompt.attachment` 的缓存/重询问合同仍见目标声明，清理投影与改 transcript 是不同操作。相关保留策略见 [Context retention](context-retention.md)。新类型没有给出“所有 reminders 都已可结构化重写”的结论。
