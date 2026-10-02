# 实验设计与证据

当前包含三项 handler-level 合成复现，其他项目是待执行设计。上游源码阅读不算实验通过，已有讨论中的测试叙述也不算本 repo 的新结果。

## 首份离线复现：roof-mod 的边界

2026-10-03，对 `kagamiurayama/claude-code-roof-mod@888dceb88631186dfcf01d69b088bedec9c1009a` 使用 [roof-boundaries.mjs](roof-boundaries.mjs)，直接调用原 module 注册出的 handler，stub `next` 为原样回传。本轮运行使用 Node.js v26.7.0。全部输入为合成材料，无模型、网络、CC 进程或用户配置。

```sh
node experiments/roof-boundaries.mjs .cache/upstream-sources/kagamiurayama--claude-code-roof-mod
```

先取得并阅读该 exact revision 的本地 checkout；`.cache/` 不随 repo 分发。脚本会执行该 module，请勿指向未经阅读的不同源码。测试中的 preamble 从源文件读取，不在本 repo 复制原厂长提示。

三项实际输出：F02 引用内 preamble 被删除；F03 构造的非 engine 同类型事件被静音；F04 channel guard 文本保留，但同段 preamble 仍被删除。脚本以这些缺陷成功复现为退出 0 的条件，**退出 0 不表示插件满足保真合同**。F03 只说明 handler 不符合自己的来源承诺，未证明 CC 会发出该来源/类型组合。

此复现未使用官方 `claude plugin test`，不证明真实 Mods API schema、加载、最终 request 或模型行为；后续采用时仍需目标 build 的事件类型与真实路径验收。

## 先做离线可反驳的检查

| ID | 合成场景 | 应观察的结果 |
| --- | --- | --- |
| F01 | engine 包装与内嵌引用包含相同短语 | 只改变允许的包装部分；原文保真 |
| F02 | 指令文件代码块引用旧模板开场白 | 期望保真；已在上述 snapshot 复现缺陷 |
| F03 | 相同 reminder type，来源不同 | 期望先按来源判断；已在构造输入下复现缺陷 |
| F04 | 外部 channel / quoted context | 期望所有阶段同范围保护；已复现缺陷 |
| F05 | reminder 带任务、工具输出或错误动态值 | 去掉语气后必要事实与可见交付约定仍有位置 |
| F06 | marked hook attachment + 普通消息 + 未标记 attachment | 只修改约定对象；UUID/parent 链条与原件可恢复 |
| F07 | Mods module 缺失、被跳过或规则未命中 | 不把 session 存活或一个 load marker 当作规则成功 |

fixture 必须由此 repo 新写，或在明确来源和许可范围内采用；不导入真实对话、账户或私人配置。官方测试入口见 [Mods testing](https://code.claude.com/docs/en/plugins/mods/test)。选定实现后再写匹配其真实合同的 tests，避免对尚不存在的 parser 编造 API。

## 再比较完整生命周期

以下对 [A/B/C 三组](../docs/profile-design.md) 都适用：

| 场景 | 检查 system / tools / messages 的什么 | 行为观察 |
| --- | --- | --- |
| 新会话 | 默认 sections、自己的 core、初始 instruction/context | 身份与任务理解 |
| Read / nested instruction / `@文件` | 后续插入位置、原文、文件状态事实 | 引用和文件使用准确 |
| Skill | discovery、skill 正文及额外指导 | 相同方法是否实际执行 |
| Bash / MCP / 后台任务 | 工具描述、server instructions、结果与提醒 | 可用性、失败解释、可见交付 |
| 普通与 fork subagent | 两种分支各自的 prompt 与历史 | 继承边界、交付质量 |
| 全量/局部 compact | 摘要请求来源、模板和进入下一阶段的摘要 | 承诺、未完成事项与表达连续性 |
| resume / continue | system snapshot、旧 reminders、重放事实 | 旧配置残留和新配置生效时点 |
| 旧 hook context 清理 | 磁盘记录与下一个实际 request 是否一致 | 不把文件编辑当作历史重建成功 |

同一模型、同一任务、同一 skill、尽量一致的工具能力；记录运行模式、prompt caching 和 snapshot 差异。至少包含一个真正需要探索的合成问题和一个能验证工具结果交付的任务，不能只测问候。

## 真实请求实验的准备

未来获授权后，在隔离安装/目录中使用合成任务，记录 CC version、安装方式、profile revision、Mods 加载结果及 request 来源。官方 raw-body file mode 是观察候选；先确认目标 build 的 telemetry 和 exporter 条件，输出保存在 Git 外，并检查没有意外的外部 exporter。[官方 monitoring](https://code.claude.com/docs/en/monitoring-usage#api-request-body-event)

`cchistory` / trace 类方案可能实际发模型请求；binary patch、清理 transcript、重启 runtime 也有独立副作用。当前研究不运行它们。不能把不支持某个事件的探针输出或模型自述用作“已经没有默认指导”的唯一证据。

## 结果怎么写

每个已执行实验留下简短 record：问题、profile/版本/上游 revision、合成输入、预期、实际、未覆盖范围、可复现步骤，以及是否采纳。具体失败必须保留；不把没有运行写成通过。

原始请求与私人工作记录留在 Git 外。Repo 只保留足以复现结论的合成 fixture、脱敏事实和自己的归纳。离线结果、真实 request、运行行为和 owner acceptance 分别标注。
