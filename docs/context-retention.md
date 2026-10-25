# Context 保留与“阅后即焚”

观察日期：2026-10-05。研究对象是动态 context 的有效期、投影与恢复。本文没有启用 transcript pruner、删除真实消息或修改任何 runtime。心跳与入站消息怎样触发下一轮，见 [Heartbeat / channels](heartbeat-and-channels.md)；跨窗口重建见 [Continuity](continuity-and-memory.md)。

## 先说明什么已经“读过”

动态状态经 hook 产生、进入 transcript、进入一个 request、模型完成任务、用户收到交付，是不同的观察点。一个时间 banner 可以在下一轮被最新值替代；尚未交付的结果、授权范围和未完成任务需要保留更久。不能用统一的“过一轮就删”处理所有来源。

| 保留对象 | 清理实际改变什么 | 单凭它不能证明什么 |
| --- | --- | --- |
| 下一次注入 | producer 停止重复发送旧值 | 先前已进入历史的值也消失 |
| 本轮 context 投影 | 从本轮输入中省略选定内容 | archive/transcript 已删除；下一轮或 resume 也省略 |
| 进程内 conversation | 当前运行中的历史视图改变 | 磁盘恢复路径使用同样视图 |
| 落盘 transcript | 恢复素材被改写 | 活跃进程重新读盘；模型已正确使用被清理内容 |
| 外部 channel 消息 | 外部服务所保存或显示的记录改变 | CC 的历史副本、工具结果、备份也删除 |
| 长期 Memory / archive | 持久来源和可检索性改变 | 只是清掉临时状态、没有丢失恢复线索 |

当前官方 Hooks 文档确认 additionalContext 会保存在 transcript，resume/continue 重放过去的中途 hook 文本；SessionStart 则可在恢复时重新运行。因此“每轮发新状态”和“旧状态退出输入”要分别设计。[Hooks：Add context for Claude](https://code.claude.com/docs/en/hooks#add-context-for-claude)

## 几种实现位置

| 方式 | 适用问题 | 维护代价与边界 |
| --- | --- | --- |
| Producer 按变化注入 / 在同一 composer 中替换快照 | 避免重复发送静态规则和完全相同状态 | 可降低新增重复；不会撤回已经入历史的注入。顺序由同一执行路径显式保证 |
| 原生 request 投影 | archive 保留，当前输入按来源/时效选择 | 需要 harness 真正拥有 messages 投影入口。Pi 的 `context`/`context_with_system` 是已读公开对照；不是 CC 自动具有的能力 |
| CC Mods `prompt.attachment` | 改或省略选定 attachment 的呈现正文 | 已读声明描述结果按 attachment 缓存，resume/invalidate 会重新询问；不能直接当成 TTL 或一次性注入。origin 也不足以确认整段都属于自有来源 |
| CC Mods `prompt.submit` 附加 context | 在原话旁自动供给环境、状态或召回片段 | 目标声明允许 hook 在 `next` 前附加；这只是注入入口，没有因此证明 TTL、旧片段撤回或 resume 策略 |
| 标记式 transcript pruning | 清除自己的旧 hook attachment 内容，同时保留记录外壳 | 直接修改恢复素材，依赖文件格式、writer 协调和活跃进程行为；最需要版本绑定验证 |
| Compact / Forge 重建 | 在较大生命周期边界重新选摘要、tail 与运行事实 | 保留原 archive 可恢复；摘要与状态选择可能失真，需要语义验收 |
| 外部 mailbox / state store + 按轮取快照 | 最新状态、待处理消息、交付状态拥有独立 owner | 需要明确读取、确认、关闭与重试语义；本文只研究合同，不重建另一套生产控制器 |

Pi 的对照来自 [固定 revision 的 extensions 文档](https://github.com/earendil-works/pi/blob/76dfb88f63ce51ff2e3fe2ead4fcf1f65f71f121/packages/coding-agent/docs/extensions.md)，阅读范围见 [Continuity](continuity-and-memory.md)。CC 的 `turn.step` 在本次目标 types 中只有 pinned `messageCount`，没有可任意重写的 messages 字段；不能凭“在请求前触发”就编造通用历史过滤器。目标声明与 probe 见 [Target runtime](target-runtime.md)。

## 历史教程的原函数复现

本轮完整阅读了一份本地历史 Markdown 教程（208 行，扩展名不影响内容），包括说明、Python code fence、接入配置、sentinel 与验证段。未取得可公开引用的原文 URL；原件和定位留在 Git 外。本页只记可复用机制与原创合成结果，不复制第三方实现或私人材料。

其核心算法选择 `attachment` / `hook_additional_context` 且命中 marker 的行，将整组 `content` 清为空字符串列表，保留其他字段，备份后原地写回。这个选择能避开用户消息里相同 marker 的引文，但有以下实证边界：

| ID | 合成输入 / 故障 | 原函数实际结果 |
| --- | --- | --- |
| B01 | sentinel 不存在 | 不启用 |
| B02 | sentinel 存在但读取失败，session 不在原 allowlist | `_enabled` 返回 true；失败会扩大为启用 |
| B03 | 文件中同时已有旧条和最新一条 marked attachment | **全部清空**；不是算法主动选出“最新一条保留”。UUID/parent 字段保持，备份含原内容 |
| B04 | user 正文引用 marker、unmarked attachment | 两者原样保留 |
| B05 | `content[0]` 命中 marker，后续项含其他 payload | 整个数组清空，后续 payload 一起丢失 |
| B06 | marker 仅在 `content[1]` | 不命中，不清理 |
| B07 | 未解析成功的 JSONL 行与 marked 行并存 | 未解析行原样保留 |
| B08 | 写入已经改变文件、在 truncate 前抛出异常 | 文件可能成为非法 JSONL；备份存在，但没有自动恢复 |

以上 8 项已运行，通过表示**这些观察成功复现**，不是算法满足当前 runtime 的安全或保真合同。所有写入发生在新建临时目录，原教程只读；没有 CC 活跃进程、真实 transcript 或模型请求。

```sh
python3 experiments/burn-after-reading.py '<reviewed-tutorial-file>'
```

[Fixture](../experiments/burn-after-reading.py) 从已审阅文件读取唯一 Python code fence 并执行它，再将操作目标设为合成临时文件。它不随仓库分发教程，不是任意 Python 的 sandbox。输入应是同一份已审阅原件；不能指向真实 transcript。

## 需要修正的四个推论

**settings 顺序不构成清理先于注入的保证。** 历史教程依赖多个 UserPromptSubmit handlers 顺序运行；当前官方文档说明匹配的 hooks 并行执行。若两个自有步骤需要顺序，应由同一个可审阅执行路径显式串联；串联仍不能证明活跃 CC 进程会重新读取改过的 transcript。[Hooks：Hook handler fields](https://code.claude.com/docs/en/hooks#hook-handler-fields)

**同 inode 与 flock 不等于完整写入协调。** 原地写避免 inode 替换，但另一个 writer 是否遵守同一把 advisory lock 仍需源码或运行证据。教程的笼统“2.1.x 实测”不足以约束每次版本升级。这里没有复现真实 CC 并发写入，也未据此选择 atomic rename 作为替代。

**捕获异常不等于回滚。** B08 给出了写入改变后异常的反例；函数外层忽略异常只能让 hook 退出，不能使之前的字节恢复。原件备份提供恢复材料，还需要实际恢复机制和验证。

**磁盘里只剩一份不等于当前输入只剩一份，更不等于零 token。** 需要分别观察活跃进程的下一次请求、resume 后请求，以及 wrapper/元数据是否继续进入输入。备份仍保留原文，所以这里的“焚”也不代表保密意义上的不可恢复删除。

## 与心跳和 channel 合起来验收

下列是待执行的跨机制案例，不是已有 runtime 功能：

- 同一状态连续心跳三次：动态快照可只保留最新值；未处理任务与尚未交付结果继续保留。
- 用户已经关闭任务，旧 tick 晚到：唤醒时重读当前关闭状态，不按旧调度文本重新开始。
- channel 消息已接收，但发送结果未知：不能以“读过”删掉交付状态，也不能无依据重发产生第二份外部动作。
- 当前窗口退出、resume 或 Forge 后：恢复须重建最新动态状态，并保留来源、未完成动作及必要的去重线索。
- hook 输出包含混合来源：只能清理自有且明确过期的部分；无法拆开时保留原文，先修 producer 的分区。

当前较稳妥的研究方向是：让自有 producer 输出可辨认的状态快照，保留 canonical 任务/交付状态，优先在已证实的 context 投影入口管理有效期。transcript pruning 继续作为独立、有版本条件的实验，不由这份研究自动启用。
