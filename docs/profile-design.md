# 自有 context profile 的设计目标

状态：前半（A/B/C 比较目标与判断标准）是**研究设计**，未实现安装器或 executable profile schema；不把尚未验证的开关写成可直接部署的配置。文末[第一份候选 profile](#第一份候选-profilecc-context-labv0未部署) 是**候选形态**（scope 约定 + 一个未安装的离线 candidate），与本节的抽象设计目标分开；候选不是最终身份，也不是 C 组完整实现。

## Profile 应能回答的事

一份 profile 应说明 core、工程方法与 skills、项目材料、记忆/状态、工具说明、reminders 和历史恢复各由谁写、何时进入、保留多久、如何验证。身份与表达不必缩成几句追加提示；参数、来源、权限与可见交付必须准确。

| 部分 | 要固定的内容 |
| --- | --- |
| Core | 身份、交流方式、判断与行动原则；引用自己的 authored source |
| Task methods | 当前任务需要的 skills；哪些常驻、哪些按需 |
| Runtime facts | 可用工具、cwd、时间、失败和后台任务状态；由真实 runtime 提供 |
| Project / memory | 来源 authority、选择方式、注入时机、时效；保留外部正文 |
| Rewrite rules | section/type/source/scope 与具体目的；不使用整段全局清洗 |
| Lifetime | 首次加载、每轮刷新、compact、resume、普通/fork subagent 的继承规则 |
| Observation | 目标版本、profile revision、装载/命中/request/行为的不同证据 |

## 三组完整比较

| 组 | 装配方式 | 要回答的问题 |
| --- | --- | --- |
| A：native + append | 默认 CC + 自有追加指导 | 常见使用基线是什么 |
| B：replace-core | 相同自有意图改用主提示整段替换，其他注入保持 | 单独换主提示带来什么变化 |
| C：owned-context | 替换主提示 + 来源控制 + Mods 或有依据的 patch，重新接入必要事实 | 完整 context 控制是否改善体验且保持能力 |

C 的完整目标保留；允许按依赖逐步实验，但不能把“成功改掉一句提醒”记为 C 已完成。A/B/C 是待比较设计，不代表已有三份生产配置。需要 `--bare` 的实验单独成组，因为认证与运行能力也变了。

模型、任务材料、用户意图、可用工具与 skill 正文尽量保持一致。记录实际差异：如技能清单被关了，就先恢复可比较的发现路径，或把差异写成实验变量。否则不能把能力缺失误归因为 prompt 质量。

## 如何判断值得保留

- 任务材料与引用内容保真，运行事实足够完成任务。
- 工具结果能形成用户实际收到的非空交付；工具有输出不代表用户看到了。
- 探索能因证据改变方向，保持问题开放度，避免过早收成工单；评估时用同一份研究 skill。
- resume / compact 后仍能保留承诺、当前事实、来源边界和自有表达。
- 分别记录 prompt 变化、token/缓存变化、实际行为和维护成本，不用单一节省比例作结论。

来源支持入口，不支持效果预测。效果需要 [experiment matrix](../experiments/README.md) 中的真实结果。

## 第一份候选 profile（cc-context-lab:v0，未部署）

状态：候选形态 + 离线 candidate，**未安装、未在模型会话启用、未发模型请求**。这是本 repo 的第一份自有 CC context profile 决策；可执行形态见 [experiments/context-profile](../experiments/context-profile/README.md)。按公开 types（`anthropics/claude-code@2bfb629dfaff0c8318047a4beb93cf1dc5b58b18`，header 2.1.277）设计；2026-10-05 已通过官方 **2.1.289** strict validation 和 test kit 3/3，Node tests 14/14。随后本地命令探针已取得 **2.1.289** 生成声明并观察真实 composition，覆盖和限制见 [target runtime](target-runtime.md)；仍不猜未证字段。candidate 合成 core 只是公共示例，不是最终身份。

### 各来源的目标处理

| 部分 | 谁写 | candidate 是否接入 | 保留 / 处理 |
| --- | --- | --- | --- |
| Core（身份、判断、行动原则） | 自有 `prompt.compose` 追加 session section（`lab:core`），引用本 repo authored source | **是**（`prompt.compose`） | 放 `session` scope、**去重后置于 shared/session 边界**；engine sections 相对顺序与字段保留；同 id 不重复 |
| System 默认指导 | engine | **机制已接入，默认选中 0 段**（`prompt.section`） | 按显式 `name` 定向替换；未选中/未知 name 透传。测试使用合成 selector；目标版本可改默认段的映射未证（见下） |
| 工具说明 | engine | **是**（`tool.describe`） | 只对 engine/core provider 的工具改 `description`；result 只有 `description`/`isDeferred?`；参数 schema、权限、工具实现不变 |
| 初始 CLAUDE.md / instruction files | engine 从磁盘加载 | **否**（`prompt.context` 未注册） | 未来若要处理初始 `instructionFiles` 才接入；当前候选不声称已接入 |
| 动态 reminders / hook context / 外部引用 / 工具交付 | engine / hook / plugin | **否**（`prompt.attachment` 未注册） | 无 handler 即无改写，engine 原样发送；**profile 明确不因 type/origin 就删载荷**——公开 extract 显示某些 engine 任务 reminder 正文含实时任务列表（todo_reminder 与它的对应未证） |
| Runtime facts（cwd、时间、工具、失败/后台状态） | engine | 保留 | 改写只针对有确证的静态指导，不删运行事实 |
| Compact / utility | engine（`session.compact` 接口存在） | **否**（未注册、未实现 handler） | 见下「compact 策略」；不实现模型 writer |
| Lifetime（resume / subagent / fork） | engine（不同 loop） | 未涉及 | 主路径规则不自动外推到 subagent/fork；分别留观察项 |

### 改写规则（scope 与目的）

- 只按 **section name / compose id / tool name + provider** 定点处理，**不做全局字串替换**，不把「字串相同」当可改写权限；lookup 用 own-property（Map），`toString`/`constructor` 等原型名一律视作未知。
- 外部来源正文（文件引用、`@文件`、CLAUDE.md、hook additionalContext、工具结果）**保真**。
- 未知 event/section/attachment type：**默认 no-op 透传**（`next(e)` 原样返回），并在 profile contract 里显式声明，而不是猜测性删除。
- 不改 tool 参数 schema、权限与工具执行实现；「未注册相应改写」是源码边界，不等于做过真实 schema/result 实验。

### 未证的选择器

`prompt.section` 的 `e.name` 是 engine 具名 section 名。已缓存官方 types 的注释给出例子（`env_info_simple`、`memory`），**存在具名 section 不代表某段语义可改**。`doing_tasks` 无证据；默认 profile 选中 **0 个 engine section**。候选用源码 `sectionOverrides` Map 显式配置，唯一导出的 `register(on)` 注册时取 snapshot，默认为空。Node 测试只注入原创合成 selector `lab:synthetic-guidance` 验证机制（选中改写 / `text:null` 保留 / 未选中保真 / 原型名视作未知），不推定任何真实 engine 段可改。注意 `PromptComposeSection.id`（组合列表 id）与 `PromptSectionInput.name`（section matcher key）是不同字段。

官方分析器实际拒绝了此前的 factory 导出；现已退役该入口，所有 tests 共用直接导出函数。版本升级先走 [官方离线检查](maintenance.md#检查指定-cc-版本的-candidate)，再依据具体缺口安排其他证据；当前通过范围见 [compatibility record](../references/context-profile-compatibility.json)。

### compact 接入策略（接口证据 + 明确策略，未接入 writer）

公开 types 支持 `session.compact` 改 `instructions`、`next({ ...e, messages })` 改被摘要内容、或直接返回自写整组 messages。**本 profile 不实现自己的 summarizer/model writer**，因为：

1. 目标 2.1.289 的 compact 字段已核，但未执行 compact；摘要安装与后续重载仍需运行证据；
2. 全量 / 局部 summarize 的内部模板是否都经该事件未证（见 [compact control](compact-control.md)）；
3. Relata/Tilia 等外部系统拥有记忆的选材/存储/检索，本 repo 只关心其产生的 context 如何被完整装入与重载。

candidate **未注册 `session.compact`、也没有任何 handler**；本文只记录策略方向（compact 后的重载可走 `SessionStart(source='compact')` 自有 hook），不写占位 handler 冒充实现。

### 剩余缺口（诚实列出）

- 2.1.289 已有官方 tests、目标 types 和一次 local print/lean composition 证据；其它 model/模式、实际 HTTP request 与模型行为未验。此处没有把本地命令加载当成生产启用。
- 目标 `attachment.detail` 仅声明三类 plan-mode 结构且可缺省；其它动态载荷未有结构证据，因此当前 profile 不依赖它。
- nested CLAUDE.md / Read 触发的后续加载是否发 `prompt.attachment` 事件未证（agents-md README 明说还不是事件）。
- subagent/fork 是否继承同样的 section/attachment 规则未证。
- 效果（行为、token）未测；不声称安装、生效或模型质量。
