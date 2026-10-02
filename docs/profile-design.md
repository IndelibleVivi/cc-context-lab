# 自有 context profile 的设计目标

状态：研究设计，未实现安装器或 executable profile schema。这里先约定要比较什么，不把尚未验证的开关写成可直接部署的配置。

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
