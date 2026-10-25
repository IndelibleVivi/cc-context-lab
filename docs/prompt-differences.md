# Named prompt 目录的组成与对应

核对：2026-10-05（Asia/Singapore）。本文回答 `lobotomized-claude-code` 的 named prompt 集合（旧版 9,491 个 `.md`）**怎样组成**：哪些是导出副本、哪些是版本/变体、哪些是实质 override。这是静态正文对应，不是运行证明；机制入口见 [upstreams](upstreams.md)，reminder 逐项见 [reminder overrides](reminder-overrides.md)，候选 profile 见 [profile design](profile-design.md)。计数与逐类依据见 [prompt-differences.json](../references/prompt-differences.json)；可复现脚本见 [compare_prompt_inventory.py](../scripts/compare_prompt_inventory.py)。

## 结论先行

旧 pin 的 `system-prompts-lcc/` 有 9,491 个 `.md`；本轮读到的 tip [`b867bb28`](https://github.com/skrabe/lobotomized-claude-code/tree/b867bb28a338de4487996fdbdff02ed54906f170/system-prompts-lcc)（作者标 CC 2.1.288）有 9,771 个。**文件数不是改写数**。用**同版本基线**（作者自己的 extractor 产出 `tweakcc-fixed/data/prompts/prompts-2.1.288.json`）把文件名当作 pristine id、逐文件分类：

| 类别 | 数量 | 判定 | 能否据此说“作者未改” |
| --- | --: | --- | --- |
| exact | 3,598 | header 移除并 strip 后的 body 与 pristine pieces 拼接相同（非原始文件逐字节） | 仅该 body 相同；不外推作者历史未改 |
| norm_only | 5,128 | 仅「空白 + `${...}` 占位符名」归一化后相同（归一化不删 `$` 字符） | **不能**：占位符名改变可能有意义，不能擦掉后声称未改 |
| changed | 805 | 归一化后仍不同 | 含实质 override 与 pristine 漂移，本统计不区分 |
| suppressed | 202 | body 为空（作者 suppress 标记） | —— |
| unmatched | 38 | id 不在本基线 | 全是作者拆分的 `inline-*` 片段 |

合计 9,771；可对应（非 unmatched）= 9,733。**用同版本基线是刻意的**：若拿旧单版去比 2.1.288 目录，会把跨版本漂移误记成差异（早一版口径曾得 unmatched 351，正是这个假差异）。复现见下。

作者 README 声明（针对 2.1.280）为 764 rewritten + 199 cut + 7,648 untouched。本次统计（`changed 805` + `suppressed 202`）量级一致，但**基线版本、归一化口径与 unmatched 定义不同**，且作者的 "untouched" 与本文的 `norm_only` 不可分离——不能等同，作者声明保留为作者报告。

## 这个目录是什么

- 扁平导出：`system-prompts-lcc/<category>-<slug>.md`，一层目录。类别前缀含 `system-prompt`、`tool-description`、`tool-parameter`、`tool-result`、`agent-prompt`、`skill`、`slash-command`、`data`、`inline`、`task`、`workflow`。
- 每个文件是 HTML 注释 frontmatter（`name` / `description` / `ccVersion` / 可选 `variables` / 可选 `nuked`）+ 正文。**正文为空即 suppress**。文件名（去 `.md`）与 CC 的 pristine prompt id 对齐；`ccVersion` 是作者对标的版本。
- 它**不是**官方 runtime 材料：是作者从安装中提取后逐条取舍的 overrides 集合。Piebald 的静态目录 [claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) 是另一份提取材料，两者都只证明「有这些候选片段」，具体进入哪次 request 受配置与条件分支影响。

## 三类组成的识别

1. **导出副本（exact）**：3,598 个 body（header 移除并 strip 后）与 pristine pieces 拼接相同。例如 [`system-prompt-identity`](https://github.com/skrabe/lobotomized-claude-code/blob/b867bb28a338de4487996fdbdff02ed54906f170/system-prompts-lcc/system-prompt-identity.md) 就是原厂那行身份句的导出。不能把导出副本计入作者改写。
2. **归一化相同（norm_only）**：5,128 个只在空白/占位符名上有差异。**不能**据此断言“作者未改”——例如占位符从 `${}` 变为有意义的 `${AGENT_INTRO_LINE}` 属于可读性变更；本文只把它记为“疑似近原样”。
3. **版本/变体**：`inline-*` 38 个是作者把原厂大段拆成的可注入片段（如 [`inline-memory-*`](https://github.com/skrabe/lobotomized-claude-code/tree/b867bb28a338de4487996fdbdff02ed54906f170/system-prompts-lcc)），没有对应 pristine id，故 unmatched；变体不是 override。
4. **实质 override（changed/suppressed）**：`changed` 805 与 `suppressed` 202 里，排除版本漂移后才是改写。典型形态（短例，不抄长正文）：
   - 收紧为肯定单句：[`system-prompt-doing-tasks-ambitious`](https://github.com/skrabe/lobotomized-claude-code/blob/b867bb28a338de4487996fdbdff02ed54906f170/system-prompts-lcc/system-prompt-doing-tasks-ambitious.md) 把原厂「你很能干……请尊重用户对规模的判断」压成一段直接指令。
   - 保留 gate、删 nag：[`system-prompt-executing-actions-with-care`](https://github.com/skrabe/lobotomized-claude-code/blob/b867bb28a338de4487996fdbdff02ed54906f170/system-prompts-lcc/system-prompt-executing-actions-with-care.md) 保留破坏性操作检查与 git status 前置。
   - 整条 suppress：[`system-prompt-context-management-block`](https://github.com/skrabe/lobotomized-claude-code/blob/b867bb28a338de4487996fdbdff02ed54906f170/system-prompts-lcc/system-prompt-context-management-block.md)（frontmatter 注明与 `inline-context-management` 近重复）、`tool-description-agent-usage-notes`（作者标 2.1.288）。

## 本次四 repo 增量的有界检查

`.cache/profile-source-refs.json` 的四个新 commit 与旧 pin 的 diff 只做**与主 system / tools / compact 有关**的 bounded 检查：

| repo | 增量 | 与 profile 相关的观察 |
| --- | --- | --- |
| [lobotomized-claude-code](https://github.com/skrabe/lobotomized-claude-code/compare/053d8703592ab7211fdf2374006d108e42f6decc...b867bb28a338de4487996fdbdff02ed54906f170) | tip 对齐 CC 2.1.288；`system-prompt-*` 改 27、`tool-description-*` 改 30、`system-reminders/` 改 0 | 新增 env-info/builtin-gh 一组、`artifact-patch-turn-*`、若干 `you-should-know-*`；coordinator-mode realign。reminder 层未变，原 41 项逐项表继续有效 |
| [tweakcc-fixed](https://github.com/skrabe/tweakcc-fixed/compare/f3cf2d9978e209cea1383a0262fa5fc7089aea50...6520e0cc06336f116b238975a6479c76a6688be6) | src/ 增量只有 `complexityRouter` 与 `refusalFallbackModel` 两个 patch | `systemReminderOverrides.ts`、`patches/index.ts` 未在 diff 中——本层 apply 语义在本增量内未见变化；同 commit 的 `data/prompts/prompts-2.1.288.json` 是本页基线 |
| [Piebald-AI/tweakcc](https://github.com/Piebald-AI/tweakcc/compare/d839e046ff8036763ddaea42197e9dc88be65b33...30909c129e2096ba993d006628e52f0e059197c4) | 仅新增 `prompts-2.1.287/288/289.json` | 提取快照，不是官方 runtime 证明 |
| [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts/compare/e6184590031d8d194074130b5e3eef7b4bbd2055...3d973c78aa7a9829d1fb576f77bb0040373f5416) | 静态目录升至 v2.1.289；新增/改 33 文件 | 含 [`tool-description-readfile-compact`](https://github.com/Piebald-AI/claude-code-system-prompts/blob/3d973c78aa7a9829d1fb576f77bb0040373f5416/system-prompts/tool-description-readfile-compact.md) 等；非 runtime 证明 |

无关变更（大量 tool-result / data / slash-command）只列覆盖限制，不逐条深读。

## 未读项与 unknown

- 38 个 `inline-*` unmatched 未逐一判定；它们是作者拆分片段，未在本 baseline 的 pristine id 集内。
- 9,733 个可对应条目只做确定性正文对应，**未逐份语义深读**。语义深读限定在主 system 核心、常用文件/搜索/执行/agent 工具、compact/utility 路径（见 JSON 的 `deep_read_targets`，含 `grep`/`glob`/`readfile`/`write`/`edit`/`bash`/`agent` 与 compact 系）。
- **section name 与可改语义区分**：`prompt.section` 的 `e.name` 是 engine 具名 section 名，官方 types 注释给出 `env_info_simple`、`memory` 等例子——**存在具名 section 不代表某段语义可改**。`doing_tasks` 在任何已缓存官方材料中无证据；默认 profile 选中 **0 个 engine section**，candidate test 只注入原创合成 selector `lab:synthetic-guidance` 验证机制。注意 `PromptComposeSection.id`（组合列表 id）与 `PromptSectionInput.name`（section matcher）是不同字段。
- **任务 reminder 载荷的 source**：候选「不整体删 attachment」的依据是 [`system-reminders/task-list-reminder.md`](https://github.com/skrabe/lobotomized-claude-code/blob/b867bb28a338de4487996fdbdff02ed54906f170/system-reminders/task-list-reminder.md)：其 body 为 `Tasks:` 加 `{{tasks}}`，而该占位符在 apply 中绑定到 `H.content.map(...)` 的**实时任务列表**（逐项表见 [reminder overrides](reminder-overrides.md)）。这证明「某些 engine 任务 reminder 正文载实时事实」，因此整类删除不成立；但该文件 id 与 Mods 事件 type `todo_reminder` 的**对应未证**，本文不作此断言。
- 未做官方全量 runtime 对照：不知道作者 tip 的锚点在任一已安装 build 上的真实命中；这些 overrides 通过 `tweakcc-fixed --apply` 拼接，本页不运行它。

## 复现

```sh
python3 scripts/compare_prompt_inventory.py \
    --overrides <system-prompts-lcc dir> \
    --pristine  <prompts-2.1.288.json>     # skrabe/tweakcc-fixed@6520e0cc data/prompts/prompts-2.1.288.json
```

脚本只读本地目录与 JSON，不联网、不安装、不发模型请求；`--json` 输出机器可读结果，输入缺失时退出 2。

## 对 profile 选择的影响

1. 这份目录的价值是**逐条意图参照**（哪里删 safety theater、哪里保留 gate），不是可直接照搬的配置，也不代表作者偏好适合本 repo。
2. 作者对 compact/utility 与主 system 的改写存在且成体系；本 repo 只**借鉴方向**（具名 section、保留 gate、不整类删），不复用其正文。
3. apply 语义在 [tweakcc-fixed](https://github.com/skrabe/tweakcc-fixed) 且本 repo 不运行它，profile 的第一实现选择官方 Mods 事件（见 [Mods migration](mods-migration.md)），把 patch 留作有具体覆盖缺口时的候选。

## 实际检查

- 9,771 个 `.md` 的 frontmatter/body 解析与五分类（exact / norm_only / changed / suppressed / unmatched），由 [compare_prompt_inventory.py](../scripts/compare_prompt_inventory.py) 对 exact tip 的 `git archive` 解包目录 + 同版本基线执行；`--json` 输出经 `python3 -c json.load` 通过。
- `references/prompt-differences.json`、`references/upstreams.json` 经 JSON 解析通过；文档相对链接 broken=0。
- 未运行 `tweakcc-fixed`、未安装、未启动 CC、未发模型请求；所有材料为公开源，示例为归纳短摘。
