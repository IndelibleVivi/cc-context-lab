# Companion input / heartbeat comparison lab

离线比较持续人–AI 相处中的自主轮次：机会从哪里来、在哪里活动、醒来带什么、留下的内容怎样进入下一轮。所有时间、天气、记忆、消息与结果都是合成 fixture；输出标为 **HYPOTHETICAL PACKET**。没有启动 CC、模型、时钟、网络、scheduler 或消息发送。

围绕一项具体选择做 A/B、保存完整来源 snapshot、逐来源检查 current/history/排除与轮后结果，使用 [Context studies](STUDIES.md)。它复用本引擎，接入 Atlas 的对照研究与变更 brief；不会建立第二个 scheduler。

`ui_only` 的环境、消息、memory 与 recall 只作预览，不能进入 current 或被 ledger 承接成 history；显式 read-only snapshot/carryover 也不能改变这个边界。原始材料仍保留在 source archive，排除原因单独记录。

## 触发位置、执行位置、历史分别选择

| 维度 | 本实验比较什么 |
| --- | --- |
| 触发规则 | 固定间隔、列举扰动、事件、自己约一次、空闲窗口、hybrid |
| 触发来源 | trace 单独记录 `external_timer`、`external_event`、`in_session_plan`、`in_session_idle` |
| 执行放置 | 主聊天跳过 `main_skip`、等聊天结束 `main_defer`、独立会话 `independent` |
| 历史方式 | 持续自己的历史 `same`、每轮 fresh 加显式 carryover `fresh` |

外部 timer 仍可能把 wake 投给主聊天。独立会话也可以长期保有自己的历史。不能只凭“外部”或“same session”判断它占不占主线程。

`turn_busy` 表示一轮回复/工具执行仍在进行，`chat_active` 表示整段人类聊天仍活跃。两者由 fixture 分别供给；实验没有实现现实中的聊天结束检测。**模型结束一次回复不等于聊天结束。**

三种 placement 是研究假设，尚未选为生产默认：

| 规则 | 对自主候选的处理 |
| --- | --- |
| `main_skip` | 如果到点或等待当前 turn 后遇到活跃主聊天，就跳过并记录原因。 |
| `main_defer` | 等到主聊天及主 turn 都空闲；解析到同一 actual start 的候选合并。 |
| `independent` | 放在独立 session，只等待该 session 自己的 busy interval；主聊天可以继续。 |

这套 gate **只处理自主候选**。普通人类消息的主聊天回复循环没有被模拟，也不该被这套 gate 阻塞。人类消息事件在实验中可以额外提出一个自主候选，消息原文同时作为有 provenance 的来源保留。

## 运行与阅读

在 repo 根目录运行，只有 Python 标准库依赖：

```sh
python3 experiments/companion-input/run_lab.py --check
```

先运行 contract tests，再为两个场景分别输出 JSON 与 Markdown 到已忽略的 `.cache/companion-input/`。仅检查用 `--check --no-run`；仅生成报告省略 `--check`。可用 `--fixtures experiments/companion-input/fixtures/common_scenario.json` 指定单一 fixture，用 `--out .cache/companion-input` 指定输出目录。

报告先给出“回复结束、聊天仍活跃”的三种放置结果，再提供六种 trigger 在 `main_defer` 下的 same/fresh 比较，以及 fixed/hybrid 在三种 placement 下的 focused 比较。没有给唤醒次数或消息数量排名。

- `common_rich_v1.md` / `.json`：环境更新、记忆纠正、只读主聊天快照、取消与内部结果。
- `quiet_and_fresh_session_v1.md` / `.json`：长安静时段、空闲观测、聊天间隙与换会话。

JSON 保留完整正文、包装、候选成员与 source archive；Markdown 显示实际文本，方便直接比较。显示时间是从 fixture 起点开始的 **HH:MM:SS**；fixture 与候选里的原始数字是秒。派生报告不进入版本库。

## 一段可复现的聊天间隙

富场景中，主 turn 在 `00:30:00` 结束，但 `chat_active` 要到 `00:35:00` 才结束。同一个固定候选 `fixed-6` 的结果：

| placement | actual start / 跳过 | 执行位置 |
| --- | --- | --- |
| `main_skip` | 跳过 | 主聊天没有自主 turn |
| `main_defer` | `00:35:00`，与其它等待候选合并 | main |
| `independent` | `00:30:00` | 独立 session |

延迟包在实际开始时重选来源：此时旧天气已过期，较新的天气、soy latte 记忆纠正及对应的自动召回正文已出现，原始人类消息及 channel/sender/time/reply/attachment 包装分别保留。

`same` 中此前确实注入过的旧天气与旧 recall 仍在历史；`fresh` 不会自动携带这些历史。这是“当前内容变新”与“旧上下文消失”的区别，实验没有删除任何真实历史。

## 实验合同与代码

| 文件 | 职责 |
| --- | --- |
| [run_session.py](run_session.py) | 生成候选、解析 placement、actual-start 准入、来源选择、session ledger |
| [run_lab.py](run_lab.py) | 组合实验、CLI、报告写入 |
| [render.py](render.py) | 完整 JSON 与可读 Markdown |
| [fixtures](fixtures) | 两段完全合成的情境；时间窗、结果与计划均为显式输入 |
| [test_lab.py](test_lab.py) | 手工推导的 placement、保留、取消、因果顺序及导出断言 |

引擎路径为 `generate_candidates → place_candidates → admit → build_packet → scripted outcome`。

- 固定节律由 `interval_seconds` 与 `duration_seconds` 生成。扰动从列举数组读取，没有随机数或真实时钟。fixture 的 `tick` 只是 idle 规则的观察点；idle 要观察完指定窗口，只生成一次机会。
- 每个候选保有 trigger owner、time、reason 与 carryover。placement 反复检查其实际开始点是否仍落在相关 chat/turn window，按允许开始点合并；多段聊天不会全部挤到最后一段结束。
- `admit` 在 actual start 逐个检查合并组成员的取消与 `run_end`。被取消的成员及其理由/carryover 不会借合并复活；只有真的准入的 self-wake 计为 consumed。
- 当前天气/记忆/recall 在 actual start 重选。记忆纠正使用显式 `corrects` 链；对应旧 recall 正文也退出 current blocks。`ui_only` 来源不进入输入包。全部 fixture 来源仍在报告的 `source_archive`，archive 不是模型输入。
- `same` 的 ledger 只存本执行 session 已接收的来源正文和已产生的内部结果，按 source ID 去重；它是上下文来源账本，**没有复刻完整逐 turn transcript 或 token 长度**。已经出现的旧块留作历史，不声称仍是当前事实。
- `fresh` 每次换 session，只按该 wake 的 carryover IDs 携带**已经可用**的材料；未产生的内部结果不会提前出现。fresh 仍会重选当前 ambient、memory、recall 与允许的人类消息来源，因此不等于空白输入。
- independent 读取主聊天原文必须在 `read_only_main_snapshots` 中点名，并且消息已经到达；same/fresh 都适用。其历史与结果只写自己的 ledger，报告可核查 main ledger 为空。主聊天快照不会变成向主聊天的注入。
- `internal` fixture 是一个预写的结果模板，分配给该时刻及以后首个准入 wake，放在该包的 `scripted_produced_results` 中，**发生在输入组装之后**。same 的后续 wake 或显式 carryover 才能读到它；本轮不能读自己的未来结果。所有 turn 的计算时长在此抽象为零，额外占用由 fixture 的 busy windows 表达。
- `scripted_outcomes` 与 `scripted_produced_results` 是报告的轮后注记；其余块描述假想输入。`internal_result_blocks` 是被选中的既往内部结果的索引视图，其完整来源也可见于 carried material；不要把这些诊断视图直接拼成真实 API messages 或相加算 token。
- `external_delivery: unknown`、silent outcome、内部结果和下一次计划分别记录。这里没有模型生成、自动计划反馈或发送成功的证据。

## 已执行与未验证

typed decision 用途现有独立的 [任务准备与 scripted replay](DECISIONS.md)，用有限选项研究一次自主机会适合什么活动，并复用本引擎的准入/来源选择。原轨迹继续作为固定 shadow 基线；决策选择不会重写后续历史。原生请求正文的离线导出见 [Heartbeat decisions](../../docs/heartbeat-decisions.md)，没有真实推理。

2026-10-05，`python3 experiments/companion-input/run_lab.py --check` 的 **24 项 checks 通过**，两份场景的 JSON/Markdown 已生成并检查关键输入。覆盖聊天间隙三种 placement、多段聊天及 busy 重叠、逐成员取消、stop、独立历史、future-source 排除、内部结果因果顺序、显式 fresh carryover、纠正/过期、原文与包装以及完整导出。

这验证的是本 lab 的显式规则。真实 CC/OpenClaw/社区实现的 busy guards、并发、重启持久性、实际请求与自然交互效果仍须各自取证；不从本实验推导版本兼容性。继续读 [心跳跳法](../../docs/heartbeat-patterns.md)、[官方机制](../../docs/heartbeat-and-channels.md) 与 [公开实现对照](../../docs/companion-source-dossiers.md)。
