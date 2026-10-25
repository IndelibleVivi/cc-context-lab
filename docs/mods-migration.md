# Overrides 迁到 Mods：入口与缺口

核对：2026-10-03。这里给出静态迁移判断，不是可安装配置。逐份 reminder 的源代码账目见 [reminder overrides](reminder-overrides.md)；CLI 与来源开关见 [official controls](official-controls.md)。

## 先处理版本分歧

本页 10/03 读取官方 `anthropics/claude-code@52c76441cae91f6891e4712306bffb057ff6fec5`。它的 [claude-code.d.ts](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/types/claude-code.d.ts#L1) 首行标 **2.1.277**，当时 Mods reference 以 **2.1.287** 为文档基线。10/05 的 reference 已标 2.1.289，新 revision `2bfb629d` 的公开 types 仍标 2.1.277；compact 补核见 [Compact control](compact-control.md)。这些材料不能拼成一个已验证的目标 runtime contract。

最直接的分歧是 `prompt.attachment`：文档说部分类型提供 `detail`；这份声明的 [PromptAttachmentInput](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/types/claude-code.d.ts#L6552) 只有 `type/text/origin/agentId`。目前没有依据编造 `detail.tasks`、`detail.content` 等字段。编写该 adapter 前，应读目标 build 在 mod 目录加载/重载时生成的 `.claude-plugin/types/`，并记录实际命中的事件；原先把 `/plugin-types` 写成命令没有依据。[Create a mod](https://code.claude.com/docs/en/plugins/mods/create#get-type-definitions-for-your-version)

10/05 自有 candidate 已跑官方 **2.1.289** strict validator 与 3 项 test kit 检查，但这两条 offline 命令**未生成目标 types**，也没有测试 attachment handler；版本/证据层级见 [compatibility record](../references/context-profile-compatibility.json)。后续独立本地命令探针已生成目标 **2.1.289** types：三类 plan-mode detail 得到字段证据，但其它载荷/真实请求仍有缺口，见 [target runtime](target-runtime.md)。

## 按入口迁移，不按文件名猜事件

下表的“候选”表示接口方向有依据，具体 reminder 是否经过它仍需目标版本取证；没有对应证据不等于必须 binary patch。

| Override 家族 | 官方入口 / source 控制 | 当前判断与需要保留的东西 |
| --- | --- | --- |
| 主 system sections、身份、措辞 | `--system-prompt-file`、`prompt.section`、`prompt.compose` | 优先用替换主提示或具名 section。插件添加的 section 用自己的命名空间；不要遍历所有 sections 全局替换引用中的句子。section 对照须从实际 composition 取得 |
| 初始 CLAUDE.md / memory 注入 | `prompt.context.instructionFiles`；`CLAUDE_CODE_DISABLE_CLAUDE_MDS` | 旧声明已支持文件的 `path/kind/content/parent`。改文件列表会由 engine 重建 framing；直接改 `claudeMd` text 会让文件信息变成 unknown。删除 preamble 与保留文件发现、tier、agent omission 不是同一件事 |
| 后续 nested memory / instructions、edited/opened/selected files | `prompt.attachment` 候选；附件总开关 | 声明列出 `nested_memory`、`instructions`、`edited_text_file` 等名字，但不能证明每条 loader 路径已发事件。引文、文件正文、路径和选择范围必须保留；旧声明无结构化 detail |
| skill discovery 与展开正文 | `prompt.attachment` 的 `skill_listing` 候选；`skill.prompt`；bundled-skills 开关 | discovery 和展开正文分开；用户/插件 skill 不等于 bundled。不能拿一个 `skill.prompt` 测试代表清单已受控 |
| agent discovery / 实际 spawn | `agent.offer`、`agent.spawn`、普通 subagent 的 CLI 追加参数 | listing 与 spawn 分别有接口。fork 共享 prompt 的路径单列；名字相同不代表是 built-in，offer/spawn 有 provider 信息 |
| MCP server instructions / per-server router | 具名 section 或 attachment 待定位；`tool.describe` 只拥有工具描述 | 没有从已读声明证明可按 server 改写聚合 server-instructions 的专用事件。`provider` 可区分 MCP 工具，却不能把 server instructions 等同于 tool description。空 router marker 会恢复 pristine 内容 |
| hook additional context / blocking / stopped | `prompt.attachment` 的 hook origin；classic hook 事件 | 保持 hook 事件名、状态、完整正文。hook 控制接口与最终注入包装是两层；不能为了删固定措辞而清掉运行结果 |
| todo / task / notification / queued message | `prompt.attachment` 候选；类型名称需现场记录 | registry 名与 Mods type 没有一一对应证据。任务状态、输出路径、工具通知、新消息正文不应随整条提醒一起消失；必须先拿到结构化事实或保留原文 |
| 工具调用、结果、错误包装 | `tool.call`、`prompt.attachment` 候选；`tool.describe` 不覆盖结果 | 不改工具 schema/权限/实现；保留结果交付、error、tool-use 对应关系。不能仅因都是“tool”就用 description 改写完成验收 |
| date / token / budget / mode transition | `prompt.context`、`prompt.attachment` 候选 | 需要区分纯指导与运行事实；删除空模板或静音整个事件是内容选择，不是天然等价迁移 |
| compact 指导、摘要结果、恢复 | `session.compact` | 已读类型支持改 instructions、待摘要 messages、返回后的 messages，或自行返回 messages；尚未证明暴露全量/局部摘要的每个内部模板。恢复来源、消息 handle 和 tool pairs 另验 |

对应声明入口：[prompt events](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/types/claude-code.d.ts#L3408)、[agent.offer/spawn](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/types/claude-code.d.ts#L172)、[tool.describe](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/types/claude-code.d.ts#L9983)、[session.compact](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/types/claude-code.d.ts#L8595)。

## 三个容易误判的边界

**engine origin 不代表整段都是 engine 原创文字。** [origin 声明](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/types/claude-code.d.ts#L6596) 明确包括用户提到的文件和运行中送入的 prompt/notification。`next.origin` 则是触发 dispatch 的 plugin/tier。来源分类可以拒绝明显越界的改写，但无法靠它识别一段混合正文中哪些字属于模板。

**改变送出的 attachment，不等于清理历史记录。** [事件注释](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/types/claude-code.d.ts#L3444) 描述：回答在 process 内按 attachment 缓存，resume 或 invalidate 时重新询问；transcript 仍保存 engine 的记录。这是 2.1.277 声明的合同，尚未实测。最终 request、磁盘 transcript、system snapshot 必须分别观察。

**compact 已有比 skip 更宽的接口，但还没有全模板覆盖证据。** `SessionCompactInput` 的 `instructions/messages` 可以改，返回值可以替换压缩后消息；保留 handle 表示沿用 engine 的原消息，自己构造消息是另一条语义。trigger 列表是 manual/auto/plugin/precompute，没有独立声明的“partial/recent template”选择项。不能以“能改 instructions”推断内部默认模板已消失，也不能反向说 Mods 只能跳过 compact。

## agents-md 的 loader 缺口已重新核对

此前仅保留为 reference 的线索，本轮已读官方 [README](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/agents-md/README.md#L23)、[register.ts](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/mods/agents-md/hooks/register.ts#L74) 与相关文件 helper。

- `managed-only` 分支只注册初始 `prompt.context` 文件过滤后返回；README 明说 engine 的 nested CLAUDE.md on Read 尚不是事件，仍会进入。这与 type 列出 `nested_memory` 并不共同证明 loader 全覆盖，应把具体路径当作待验收缺口。
- 添加 AGENTS.md 的模式在 `tool.call Read` 后把文件放进 result.context，按 loop 去重；有 attachment/simple 开关判断，普通/fork agent 的继承分别处理。
- README 还列出 `@文件`、IDE selection、非文本 Read、`--add-dir`、compact 后恢复与文件变更重通知等差异。这里只核来源说明和主注册路径，没有运行官方 tests 或把所有差异升级为当前安装的实测结论。

因此，初始文件列表能控制，并不证明后续 instruction loading 也已控制。未来完整 profile 应为初始、Read、@mention、IDE、compact/resume、普通/fork agent 分别留观察项。

## 本轮可落定的选择

优先用官方主提示替换与具名 section 构建自己的 core；动态载荷先保留原文，等目标版本的结构字段可用后再重写包装。对仍有缺口的类别，继续比较精确 patch，而不是先装整个 fork 再接受它附带的行为变更。

离线 [F01–F05](../experiments/README.md) 已能否定“只替换已知短语就不会误伤引用”与“静音提醒必然只删多余语气”。它们没有选定最终实现，更没有验证目标 build。10/05 已补 [named prompt 目录对照](prompt-differences.md) 与自有 candidate 的官方离线检查；现又取得目标 types 与一次 print/lean section 映射；剩余是其它分支、动态载荷与请求生命周期证据，按具体缺口安排获授权实验。
