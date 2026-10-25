# Forge / 精炼续窗 / Swap 上游对照

核对：2026-10-04。对象是公开 repo `dankefox/swap-tutorial` 与其链接的 `wuxuyun0606-collab/lmc-5`。
本轮做有界 source 阅读，并对选定上游参考算法运行一项离线合成复现。完整 revision、已读路径与 known unknowns 见
[catalog](../references/forge-upstreams.json)。README 与上游文档的支持范围属于作者声明，不是本 repo 的实测。

固定 revision：

| 项目 | revision | commit date | 说明 |
| --- | --- | --- | --- |
| `dankefox/swap-tutorial` | `8ce3c7df73ead621762ff38993aab29b0ecbca8e` | 2026-08-16 | main；AGPL-3.0；只有 `README.md` + `LICENSE` |
| `wuxuyun0606-collab/lmc-5` | `fb3e72c9ee7357c8b17311097b0750082a8a1237` | 2026-08-18 | main；声明版本 0.3.0；package 支持 `requires-python = ">=3.9"` |

`pyproject.toml` 的 `requires-python = ">=3.9"` 是 package 支持声明；同文件的 `target-version = "py310"` 只是 Ruff/lint 目标，
不是 runtime 要求。原函数 fixture 已在 Python 3.9.6 与 3.13.3 下通过，均符合 package 声明；这不代表运行了上游完整测试套件。
2026-10-04 统一 refs 检查确认这两个 main tips 与已读 revision 一致；当前更新状态见 [总 catalog](../references/upstreams.json)。

## 三个名字，三件不同的事

上游把三个概念分开，教程也采用这一划分：

| 名称 | 解决什么 | 上游公共状态 |
| --- | --- | --- |
| 精炼续窗 / Refined Session Carryover | 旧 transcript 太重但思路健康：过滤、打分、重写消息链，生成可 `--resume` 的新会话 | **有公开参考脚本**：`extras/claude_code/refined_session_carryover.py` |
| Forge | 窗口已污染或需从耐久记忆重建 | 在所查 repo/路径**只找到文档描述**，未找到实现脚本或 `boot-context` CLI |
| Swap | 批量写记忆数据库前后可回滚 | 在所查 repo/路径**只找到文档描述**，未找到 savepoint / snapshot 脚本实现 |

`docs/REFINED_SESSION_CARRYOVER.md` 明确要求：面向用户不要把精炼续窗叫 "Swap"，`Swap` 留给 DB 回滚
（[REFINED_SESSION_CARRYOVER.md:98-107](https://github.com/wuxuyun0606-collab/lmc-5/blob/fb3e72c9ee7357c8b17311097b0750082a8a1237/docs/REFINED_SESSION_CARRYOVER.md#L98-L107)）。

### 旧 Swap 与 LMC-5 Swap，名称搬运的证据

- 教程自述：内部曾把会话换窗叫作 "Swap / 洗脸"，公开改叫精炼续窗，LMC-5 的 `Swap` 专指 DB 快照回滚
  （[swap-tutorial README 开头](https://github.com/dankefox/swap-tutorial/blob/8ce3c7df73ead621762ff38993aab29b0ecbca8e/README.md)）。
- 上游 `docs/credits.md` 记载：transcript-resume swap 设计来自「蛋宝老师家的蛋壳」，其余 DB swap 来自 LMC-5 自己的部署经验
  （[credits.md](https://github.com/wuxuyun0606-collab/lmc-5/blob/fb3e72c9ee7357c8b17311097b0750082a8a1237/docs/credits.md)）。
- 链接方向是**单向**的：swap-tutorial 指向 lmc-5；lmc-5 全文不出现 `dankefox` / `swap-tutorial`。

因此「近期把 Swap 从会话换窗改名为精炼续窗、把 Swap 让给 DB 回滚」这一操作，证据来自两侧文本与 credits，而不是某个脚本重命名。

## Forge / Carryover / Swap 的操作映射

上游 `docs/FORGE_AND_SWAP.md` 用三个失败模式组织三件工具（原文措辞属作者声明）：

| 触发 | 工具 | 上游描述的动作 | 公共实现 |
| --- | --- | --- | --- |
| 上下文/配额到顶、`/forge`、定时 | Forge | 快照 open state → 干净终止 → 用 `--resume` + `boot_context.json` 重启，并让用户可续话 | 无脚本；`forge.sh` 只是文档里的 minimum sketch |
| transcript 续窗太脏 | 精炼续窗 | 过滤旧 JSONL → 选高信号 + 干净尾部 → 重写 `sessionId/uuid/parentUuid` → `claude --resume <new-id>` | 有参考脚本 |
| 批量写记忆（hippocampus/Z/M/迁移） | Swap | Style A 事务 savepoint / Style B 表级快照，验证失败则 restore | 无脚本；`swap()` 与 `take_swap_snapshot()` 只是文档片段 |

在所查的 `src/lmc5/cli.py` 中**未找到** `boot-context` 子命令（子命令清单：init/add/relate/relations/entities/log-event/events/search-events/surface/state-refresh/state/stats/vector-*/recall/recall-traces/list/patrol/consolidate/hippocampus/atom-audit/z-audit/doctor/import/export）。文档示例命令与所查 CLI 不一致；不排除其它 repo/路径有对应实现。

## 教程所述「作者扩展」是否有公开源码

结论：**在这两个 repo 的已读路径中没有作者那套完整扩展的源码**；教程自身也标注它们是第二阶段、参考脚本不会自带。
这不否定相邻公共能力（例如 extras 里确有启动包 builder 与冷仓 adapter），只是说教程描述的「完整套件」无法由公共 repo 直接运行。

| 教程里的部件 | 教程说法 | 公共 repo 实际 |
| --- | --- | --- |
| 启动包（boot package） | 四类内容确定性拼装后前置给新 session | 只有 `extras/pgvector_backend/hooks/session_start.py` 的 `build_startup_pack()`（`budget_chars=6000`）这一 extras 生产实现；它与 carryover 参考脚本彼此独立，且非 CLI `boot-context` |
| 叙事脊椎（narrative spine） | 四行便签、完全确定性、超 700 字整张放弃 | 公共源码**无**该构造；`docs/FORGE_AND_SWAP.md` 也未定义。`extras/pgvector_backend/narrative_timeline.py` 是做 weekly/monthly 叙事索引的另一个模块，不是教程的四行便签 |
| 冷仓（cold store） | 存被换下的完整旧 transcript，作最后证据层 | 公共 extras **有**冷仓接线与 adapter：`recall_pipeline.py:1374` 的 `cold_archive_search_adapter`，`user_prompt_submit.py:212-215` 在 `LMC5_COLD_ARCHIVE_FALLBACK` 开启时把它接进 pipeline，`recall_pipeline.py:1052-1065` 作 last-resort 调用。但这是 **recall 层的冷归档兜底**，不等同于教程作者「换窗时把整份旧 transcript 独立归档、可查证/回退」的完整流程公开可运行 |

证据引用：

- 教程自述扩展非上游自带：[README「上生产前再加四道闸 / 常见误区」](https://github.com/dankefox/swap-tutorial/blob/8ce3c7df73ead621762ff38993aab29b0ecbca8e/README.md)（原文：「参考脚本本身不会自动替你搭好这些扩展」「以为参考脚本自带启动包和冷仓」）。
- 启动包实现：[extras/pgvector_backend/hooks/session_start.py `build_startup_pack`](https://github.com/wuxuyun0606-collab/lmc-5/blob/fb3e72c9ee7357c8b17311097b0750082a8a1237/extras/pgvector_backend/hooks/session_start.py)。

这不否定作者在生产里这么跑；只是说这两个 repo 的已读路径无法佐证「整套系统开箱即有」，也不会把作者报告当作本 repo 的亲自实测。

## 真正的 carryover reference script：选择/排除规则

参考脚本 `extras/claude_code/refined_session_carryover.py` 是**确定性、无模型调用**的。规则集中在一个正则组 + `classify_event`：

保留类（按命中关键词计数，不语义判断）：

- `MEMORY_RE`（L30）：remember / preference / identity / promise / 关系 / 承诺 / 边界 … → `gold-memory`
- `STATE_RE`（L38）：current task / next step / risk / 检查点 / 阻塞 … → `state-note` / `task-checkpoint`
- 短且低噪音的对话 → `natural-tail`

排除类：

- `NOISE_RE`（L44）：Traceback / Exit code / SQL / 绝对路径 / 代码块 ``` / 行首 `{` … 按命中数惩罚或整条丢弃
- `HOOK_RE`（L53）：hook injection / recall result / 召回结果 …
- `INJECTION_BLOCK_RE`（L59）：`<task-notification>` / `<system-reminder>` 包裹块，`is_injection_block` 直接排除
- `POISON_RE`（L64）：AUP / refusal loop / 风控 / 中毒 … 用于 `recent_poison_score` fail-closed

关键阈值（[classify_event L205-238](https://github.com/wuxuyun0606-collab/lmc-5/blob/fb3e72c9ee7357c8b17311097b0750082a8a1237/extras/claude_code/refined_session_carryover.py#L205-L238)）：

- 身份/链/工具事件：`is_dialogue_event`（L189）只留 `type ∈ {user, assistant}` 且 `isMeta`/`isSidechain` 为假；content 若是纯 `tool_result`/`tool_use` block 列表则排除。
- 超长：`len(text) > 9000 and memory_hits < 2` → 整条丢弃（L218）。
- 噪音：`noise_hits >= 6 且 memory==0`、`noise_hits >= 10 且 memory<3` 丢弃（L220,222）。
- 代码块：含 ``` 且 >1800 字且 memory<2 丢弃（L224 附近）。
- 长文本截断：`compact_text`（L163-171）对超过 `max_event_chars` 的正文保留**头部 1/2 + 尾部 1/2**，中间插入 `[refined-carryover: long low-value middle omitted]`。
- 排序与预算：`select_refined_events`（L247）取 gold 前 80、state 前 20、最近 `tail_events` 个候选，**按原始 index 重排**；超 `target_tokens`（默认 50k）时从低优先级、**非 tail** 的候选开始丢，tail 候选不会被它删。这里的 `tail` 是 `candidates[-tail_events:]`，即**候选事件数**，不是「最近 14 个对话回合」也不是「raw 最后 14 条」；非对话/被排除的事件不进入候选，因此 tail 覆盖的原始事件跨度可能更大。
- 非 hard cap：预算只删非 tail 候选，且 `ensure_user_first` 在预算统计**之后**才加 sentinel，所以 `target_tokens` 只是目标值，选中结果的实际估算可以超过它（见 C8）。教程「约 48k / 最近 12 回合」是作者取值，不是脚本保证。
- 恢复格式：`ensure_user_first`（L155）在选中历史以 assistant 开头时，前缀一条合成 user sentinel。

### 能证明与不能证明

能证明（source-level）：

- 参考脚本**不会**保留 tool pairing——它把 assistant 的 content 压成单条 text（`sanitize_event`），tool_use/tool_result 结构被丢弃或整条过滤；这与教程「误区二：只截最后 N 行会截断 tool_use/tool_result 配对」的告诫方向一致，但脚本自身的处理是**重新序列化**，不保证配对。
- 选择是**关键词计数 / 子串匹配**，不是语义判断，也不验证事件 origin。同一句话是否被保留，取决于它是否恰好含 MEMORY/STATE 词；`<system-reminder>` 之类的排除只看字符串，**不能**据此把用户引用的文本当成真实运行时 injection，也不能把真实 hook 当成普通用户发言。

不能证明：

- 无法证明某次真实 resume 一定被 Claude Code 接受，或 tool pairing 在过滤后是否仍合法。
- 阈值与正则属实现细节，不是上游 schema 承诺；升级可能改变行为。
- 教程声称的生产参数（约 48k token、最近 12 回合、工具足迹）不是参考脚本默认（默认 50k / 14），属作者取值。

## 离线合成复现

2026-10-04，用 [carryover-selection.py](../experiments/carryover-selection.py) 直接加载上述 exact revision 的**原模块**（`importlib`，无算法替身、不导入上游包、不触发 `__main__` CLI），调用其自身 `select_refined_events` / `classify_event` / `compact_text` / `recent_poison_score`。全部输入为合成材料；不联网、不调用模型、不写 session 产物、不读取真实 transcript。Python 导入可能生成本地 bytecode cache。

```sh
python3 experiments/carryover-selection.py .cache/forge-public/wuxuyun0606-collab--lmc-5
```

实际输出要点（exit 0，表示观察复现，**不是**生产验收）：

| ID | 合成场景 | 观察 |
| --- | --- | --- |
| C1 | 明确身份/偏好/承诺事件（保真 control） | 原文逐字保留，`selected_gold=1` |
| C2 | 长消息中间夹一条 boundary，正文长 9086 字 | `compact_text` 输出 3653 字，中间 boundary 被丢，出现 middle-omitted 标记 |
| C3 | >9000 字且不含 ≥2 memory 命中 | 整条被拒（`classify=None`） |
| C3b | 同一条长消息加 ≥2 memory 命中 | 变为 `gold-memory` 保留，但被埋的决策仍不在输出里 |
| C4 | 工程讨论：重要决策不在尾部、无关键词 | 原句被丢弃；**同一句逐字不变**、仅前置 `Current task. Next step.` 后被保留 |
| C5 | `<task-notification>` / `<system-reminder>` 字符串（选择 control） | 命中子串的整块排除，干净消息保留；算法未验证真实 origin |
| C6 | 选中历史以 assistant 开头 | 前缀合成 user sentinel，类型序列 `user, assistant, user` |
| C7 | 一段**描述**拒绝循环/AUP 的复盘 | `poison_score=3`；fail-closed 是 `create_refined_session` / `main` 的静态分支（`poison_score >= 2`）推断，未真正执行文件写入 |
| C8 | 极小 `target_tokens=1`，含正信号事件 | 仍保留 tail，真实 selector 估算 729 远超目标；`target_tokens` 非 hard cap |

## Limitations 与未验证

- 本轮只读两个 repo 的选定路径；`extras/pgvector_backend` 的完整链路、LMC-5 core 的 store/consolidate、以及 hooks 的真实运行都未读全或未运行。
- `pyproject` 的 `requires-python = ">=3.9"` 是 package 支持声明，`target-version = "py310"` 只是 Ruff/lint 目标。3.9.6 与 3.13.3 的原函数 fixture 结果不代表上游完整测试套件。
- 未执行 `create_refined_session` / `rewrite_session` 的磁盘写入，未跑 `claude --resume`，未用官方 `claude plugin test`、真实 transcript 或模型请求。
- 作者报告的模型行为、token 统计与生产参数未复测；不为它们背书。
