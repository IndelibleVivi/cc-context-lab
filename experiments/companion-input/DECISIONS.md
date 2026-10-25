# Typed heartbeat decision（离线实验）

研究**有限选项的 typed decision**（Clef / Decisions API 式的一题单选）对伴侣自主轮次有什么用。
答案是**合成 scripted 输入**，不是 chat LLM planner，也不是模型评测。无 HTTP、无凭据、无模型调用、
无 scheduler、无消息发送——纯 stdlib 的 prepare + scripted replay。

一句话合同：把已准入的自主机会当**一道有限选择题**，记录一个**假想 intent**，但不重算后续历史、
不产生真实活动。决策是 shadow annotation。

## 运行

在 repo 根目录，只有 Python 标准库依赖：

```sh
# 跑合同测试 + 生成报告
python3 experiments/companion-input/run_decisions.py --check

# 只跑测试，不写文件
python3 experiments/companion-input/run_decisions.py --check --no-run

# 只准备任务（导出 tasks.jsonl），不消费任何回答
python3 experiments/companion-input/run_decisions.py --prepare-only

# 自定义输入/输出
python3 experiments/companion-input/run_decisions.py \
  --fixtures experiments/companion-input/fixtures \
  --cases experiments/companion-input/decision_cases.json \
  --out .cache/companion-input/decisions
```

`python3 experiments/companion-input/run_lab.py --check` 也串起本实验：先跑既有 24 项、再跑本目录
的 schema 与 integration 测试。退出码：`0` 通过；`1` 有 case 期望不满足（见输出 `VIOLATION`）；
`2` CLI/fixture 错误。

输出（默认 `.cache/companion-input/decisions/`，被 git 忽略）：

| 文件 | 内容 |
| --- | --- |
| `tasks.jsonl` | **prepare 导出**：每行一个 task，按 `(task_id, state_revision)` 去重。 |
| `replay.json` | 完整 **SCRIPTED_REPLAY** 结果：任务依据、选项、baseline、回答状态、gate 结果、假想 intent。 |
| `replay.md` | 同一结果的可读版。 |

`replay.json` 顶层标 `model_evaluation: NOT_RUN`；Markdown 标 **MODEL NOT RUN** 与
**SCRIPTED_REPLAY**。所有分支的 `external_delivery` 恒为 `false`。

[原生请求导出器](../../scripts/prepare_heartbeat_requests.py) 可把 `tasks.jsonl` 转成 native Clef-Flash 与
OpenAI Decisions 请求体（只准备、不发送），用法与 API 来源见 [Heartbeat decisions](../../docs/heartbeat-decisions.md)。
真实 provider response adapter 尚未接入。

## 任务合同（本 repo own，不是 provider wire body）

一道问题 `heartbeat_activity`，五个固定选项：

| 选项 | 语义 |
| --- | --- |
| `remain_quiet` | 这次不活动。 |
| `internal_activity` | 允许位置中的内部活动（绝不发消息）。 |
| `prepare_contact` | 准备可供后续审阅的**联系草稿**，绝不发送。 |
| `revisit_later` | 建议之后再评估，**无自动 timer**。 |
| `insufficient_context` | 上下文不足（**业务选项**，不是 error/refusal）。 |

task 是 repository-owned contract，显式标 `not_a_provider_wire_body: true`，不是任何 provider 的
tool schema、JSON mode 或 function-call body。main/independent、same/fresh 来自**显式配置**
（`selection`），不由模型擅自切换。

## 准备（prepare）

候选机会**只**从既有 fixture 经 `(fixture, policy, placement, history)` 显式选择，复用 canonical
`run_session` 的 source selection 与准入；**没有第二套 scheduler**。

- 已被 canonical placement/admit 拦下的候选（skip/drop）**不产生 task**，只记入 `audit.blocked_candidates`。
- task 的 evidence 取自**实际开始**的 packet，allowlist 提取后剥离 `scripted_outcomes`、
  `scripted_produced_results`、`expected` 标签与未来来源。
- coalesced 候选保留 constituent provenance，但**只产出一个 task**，不为每个原始成员各出题。
- 已允许的被承接历史（旧天气、被纠正前的记忆）以 `historical: true` 保留**正文**，不当 current；
  未来 / 未分享（含 independent 未点名的主聊天快照）/ `ui_only` 材料不进入 history。
- `excluded` 诊断留在报告外层，**不**进入模型 evidence。
- task 绑定一个 `state_revision`（允许的输入视图版本，单独的 prior internal 索引不参与）与 `dependency_signature`
  （consume 时用于比对依赖是否变化）。

## 回放与消费（replay / consume）

回答按 `status` 分类并区分 `ok` / `unknown` / `refusal` / `error`：

- `ok` 需合法选项；若带**完整** probabilities，则检查每项 finite numeric non-bool、范围 `[0,1]`、
  和 ≈ 1、无缺失或额外键，且选中项须为最大值之一，否则降级为 `error`。
- `confidence` 仅在 finite numeric 时保留，**不设阈值、不当正确率**；缺失时不编造。
- refusal / error / unknown **保持原状态**，即使夹带 option 也不会被改写成 `remain_quiet` 或
  `insufficient_context`。

消费包含可执行的 post-check gate（合成快照 supplied state，不声称能检测真实 CC）：

1. 回答必须显式绑定本 task 的 `task_id` + `state_revision`（漏绑定或绑错一律 reject）；
2. start 之前的回答拒绝；
3. wake 必须仍在同一 start 复现（**start 前**的取消会改变准入，因此在这里被发现）；
4. **start 与 consume 之间**参与本任务的任一 self-wake reason 被取消 → 整个旧任务失效
   （含 coalesced 的单个 constituent），避免半个合并任务继续用旧判断；
5. **start 与 consume 之间**外部依赖变化（天气过期 / 记忆纠正 / 新环境 / 新人类消息）→
   `state_revision_changed`，discard；
6. run-end / chat_active / target-busy 在 consume 时检查。

任何 discard 只记录，**绝不放行活动**；无内容变化的延迟回答仍可用。
`prepare_contact` 也只得到 draft proposal，外部交付恒为 false。
blocked/stale 的 case **不**计任何模型正确率。

## 合成病例

`decision_cases.json` 有 21 个合成病例，`expected`（`expect`）与输入分离；`rule_baseline` 只是
确定性比较基准，scripted 回答**不是**模型评测。覆盖：

- 聊天仍活跃但 turn 已结束（`chat_active_turn_ended_independent_remain_quiet`）；
- 独立内部活动、quiet ≠ 需要联系、明确稍后约定；
- 环境新鲜 → prepare_contact draft、以及过期 / 新环境 / 记忆纠正的**迟到** discard；
- start 前后取消、迟到回答时人类重新聊天、target busy、run end、start 前回答；
- unknown / refusal / transport error / 非法 probabilities（sum、extra key、非最大值）；
- 正常合法回答、coalesced 单任务、被 canonical 拦下的候选不送题。

每个 case 的 `narrative` 是**纯合成**语义情境，不从真实私聊抄写。

## 边界与未验证

- 本实验验证的是**本 lab 的显式规则**。真实 CC/OpenClaw 的 busy guard、并发、重启持久性、
  实际请求与自然交互效果仍须各自取证。
- scripted 回答不是模型输出；不评测任何模型、不比准确率。provider wire body 与外部文档证据
  见 [专题](../../docs/heartbeat-decisions.md) 与 [source record](../../references/heartbeat-decisions.json)。
- 合成快照 gate **不声称**能观测真实 CC 的聊天状态或 scheduler。

## 已执行验证

2026-10-13：统一 `run_lab.py --check` 的 **71 项**通过（原输入包 24、schema 14、决策/入口 33）；
原生请求导出器另 **4 项**通过。21 个合成病例满足明确写定的期望，去重导出 8 个任务及两种 profile
各 8 个请求正文。入口负例先复现再修复：`--prepare-only` 不依赖回答或 gold，check 失败不被报告生成覆盖，
显式错绑不被自动修正，合并机会中被移除的旧成员仍会使旧回答失效。

上述通过不提供模型质量、真实 CC 或交付证据；全部产物留 `.cache/companion-input/decisions/`。
