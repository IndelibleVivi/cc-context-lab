# 可复现的 Context studies

围绕一个具体 context 问题比较 A/B：固定完整合成材料和条件，经 canonical 引擎得到逐来源轨迹、机会对照与报告。当前提供 source、CLI 和 Atlas 集成；不启动 scheduler、CC binary 或模型，也不把输出称为捕获的 request。

## 使用

从 [Context Atlas](../../workbench/README.md#对照研究与重跑) 的“对照研究”选择条件、填写问题与保留要求，下载研究 JSON。用当前引擎重跑：

```sh
python3 scripts/run_context_study.py plan.json --out .cache/context-study
```

只需 Python 3.10+ 标准库。成功输出 `plan.json`、`result.json`、`result.md`，退出 0；非法输入、路径冲突或 I/O 失败退出 2。原输入始终保留，包括它本来就是输出目录的 `plan.json` 时，原始字节也不会被重新格式化。若 input 与 `result.json` / `result.md` 是同一文件、软链或硬链则拒绝；输出互相 alias 或非普通文件也会拒绝。

校验和报告序列化在写文件前完成；每个文件先临时暂存再 atomic replace。它不是跨三个文件的事务，若中途遇到 I/O 失败，可能只更新部分报告，命令会返回失败。

可将自定义或旧 snapshot 生成可检查的页面：

```sh
python3 scripts/build_context_atlas.py --study plan.json --out .cache/context-study/atlas
```

同名内置情境在派生页面中由 plan snapshot 替换，原始 fixture 文件不变。浏览器恢复只接受与当前投影一致的材料与可用条件；不一致时会拒绝并保留当前研究。页面没有本地自动保存，离开前下载 JSON。

## Plan 合同

`PLAN_SCHEMA = "cc-context-study/1"`。唯一执行逻辑在 [context_study.py](context_study.py)，CLI 为 [run_context_study.py](../../scripts/run_context_study.py)。顶层字段：

| 字段 | 含义 |
| --- | --- |
| `schema` | 固定的 plan schema |
| `title`, `question` | 非空研究标题与问题 |
| `preserve` | 研究者声明的保留要求；不是已通过的断言或模型 gold |
| `fixture` | 完整合成 snapshot：scenario_id、shared、policies、placements、timeline、outcomes、duration_seconds，以及原有说明字段 |
| `baseline`, `candidate` | 各含 `policy_id`、`placement_id`、`history_mode`（same / fresh） |

plan 不接受额外顶层 command/path/provider/execution 字段，不解析成生产配置，也不授予外部调用。fixture 是数据，保存原话、环境、纠正关系、预写结果与时序；不按 scenario_id 查找并替换成本地新材料。

`validate_plan(plan)` 返回独立 deep copy；错误以带字段定位的 `ValueError` 拒绝。校验来源 ID、规则/位置组合、引用、非负整数时间、重复候选 identity、正数 interval 等 canonical 引擎前提。单个周期规则超过 10000 个周期机会时会拒绝并要求缩小合成 horizon，避免导入数据无界展开。

`run_study(plan)` 分别调用 `run_session.run_comparison`，返回 `cc-context-study-result/1`：原 plan、分层 evidence、changed_axes、comparison_kind，以及两侧的 selection / run / observations 和 comparison。多轴改变标为 compound；相同配置也是有效对照。不按次数、来源数或 token 数给配置排名，不从多轴变化写单因果结论。

## 观察投影

`project_run(fixture, run)` 接受 raw fixture 或 canonical Fixture 与一次完整 run，返回 `cc-context-study-observations/1`。它索引现有结果，不重算 scheduling 或 source selection。

- `sources[]`：完整原始 payload、provenance、每轮 exposures、produced_after_input。provenance 的 fixture_time 是源事件时间，不代表已经进入输入；内部结果的实际产生另按 producing wake 记录。
- `exposures[]`：wake_id、actual_start（合成秒数）、actual_start_text、current/history/excluded/present/produced_after_input 布尔值、channels 和选择/排除 reasons。一个来源可以同时处于 current 和 history，也可以已从 current 排除而仍在 history。
- `packets[]`：该轮实际 current（每块包含 channel 和完整 payload）、history、excluded、produced_after_input，以及 session identity 与目标。prior_internal_result 是此前产生的内部结果；本轮新结果只在轮后位置记录。
- `opportunities[]`：原始 trigger ID、触发来源、时刻、admitted/skipped/dropped、对应 wake/actual start、合并成员和原因。

`compare_observations` 只在两侧 policy 相同的情况下按 constituent trigger ID 对齐，保留多对一合并、跳过、取消与未匹配。不同 policy 标 `cross_policy_not_compared` 并分列，不能按 packet 数组下标或邻近时间造对应关系。逐来源对照以同一 snapshot 的 source ID 为单位。

原话的原始 sender/time/channel/attachment 等保留在 source payload；实际变换后的 user wrapper 留在 observations.current 与 canonical run。current 退出不等于历史删除，archive 存在也不证明正文曾经送达模型。UI-only 环境、消息、memory 和 recall 不得进入模型输入或历史，原件与排除理由仍可检查。

## 报告与验收

CLI Markdown 与 Atlas Markdown 都展示 canonical 投影的实际条件与轨迹；CLI 另保留完整 canonical A/B run 和 comparison JSON。Atlas 把研究带入 brief 时固定 plan 和已生成报告，之后编辑当前研究不会静默改写附件，可明确移除或重新带入。

```sh
python3 scripts/test_context_study.py
python3 scripts/test_build_context_atlas.py
node --test scripts/test_study_ui.cjs
# 完整 authored-source 离线 gate
python3 scripts/check_offline.py
```

检查覆盖旧天气退出 current 仍保留 history、recall 纠正、原话与 wrapper、轮后产生再承接、合并 identity、cross-policy/compound、snapshot roundtrip、错误输入不损害当前工作及 CLI 不覆盖输入。界面仍需实际检查，构建或语法通过不替代浏览器验收。

保存的是固定输入与配置，**不包含引擎源码 snapshot，也不保证跨代码版本相同结果**。真实 request、自然语义、scheduler、安装/激活与交付保持未验。typed decisions 仍是独立 shadow 实验，本研究没有按其意图改变后续 ledger。programme 见 [连续建设](../../docs/development-programme.md)。
