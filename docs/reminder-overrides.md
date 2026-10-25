# system-reminders overrides 与实际 apply 路径

核对：2026-10-03。范围是本专题的 source-only 阅读：`lobotomized-claude-code` revision `053d870`（`system-reminders/`，41 个 `.md`）与 `tweakcc-fixed` revision `f3cf2d9` 的 `src/systemReminderSync.ts`、`src/patches/systemReminderOverrides.ts`（并借读 `src/systemPromptSync.ts` 的 shadow 扫描、`src/utils.ts` 的 `escapeNonAscii`）。离线证据来自已执行的 [experiments/reminder-placeholders.mjs](../experiments/reminder-placeholders.mjs)（P01–P05 全 PASS），它用 Node `stripTypeScriptTypes` + `runInNewContext` 在内存中执行若干纯 apply 函数与合成 bundle 形状——不是文件系统 apply driver、不是安装、不是真实 CC。没有安装依赖、没有运行文件系统 apply driver、没有触发真实 CC reminder；**runtime_verified = false**。逐文件字段化清单见 [references/reminder-overrides.json](../references/reminder-overrides.json)。

## 这层机制怎么走

1. `parseReminderMarkdown`（[systemReminderSync.ts L18-38](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/systemReminderSync.ts#L18-L38)）用 HTML 注释（`<!--` / `-->`）当 frontmatter，读 `name` / `description` / `ccVersion` / `placeholders`；正文去首尾空行后 `isSuppressed = body.trim()===''`。注意 parser **不读 `shadows`**。
2. `shadows` 由 `loadShadowSet` 单独并集（[systemPromptSync.ts L32-75](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/systemPromptSync.ts#L32-L75)）：一个来源是 `system-prompts/*.md` 与 `system-reminders/*.md` 的 frontmatter，另一个是 `REMINDER_REGISTRY` 各条目的硬编码 `shadows`。两边都不校验被声明的 id 是否真在 prompt catalog 中。
3. `substitutePlaceholders`（[systemReminderSync.ts L114-156](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/systemReminderSync.ts#L114-L156)）用正则 `\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}` 扫描：花括号内的名字两侧允许可选空白（`\s*`）。不在 whitelistMap 的名字记 error 且 result 置空（未知 token 被拒，P05 验证）；已知名字走 `body.split(tokenRe)` 切分——非 token 段转义（反斜线、反引号、`${`，最后 `escapeNonAscii`），token 段直接取 `whitelistMap[名字]` 原样拼回，再 rejoin。所以已知占位符**会被插入**，只是插入发生在 split/rejoin 而非整体 replace。
4. `applySystemReminderOverrides`（[systemReminderOverrides.ts L1889-1987](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/patches/systemReminderOverrides.ts#L1889-L1987)）对每个 registry 条目 `ensure → load → substitute → apply`。结果语义（L1966-1983）：apply 返回 `null` 记为 `failed:true`；否则 `applied = next !== working`，即便 `next===working`（无变化）也是 `applied=false, skipped=false`；`skipped=true` 只出现在 override 文件缺失（ensure 后仍读不到）的分支。**“无变化”不等于 skipped。**

## 覆盖与不一致（先看这几条）

- **数量**：41 个 reminder 文件 vs 35 个 registry 条目。41 = 34 个内容 apply 条目 + 1 个 marker（`mcp-per-server-router`，本身不发内容）+ 6 个 `mcp-<name>.md` per-server 文件（无独立 registry 条目，靠 router 在运行时按 server 名读取）。35 = 34 内容 + 1 marker。另注：`mcp-instructions.md` 属那 34 个内容条目之一，`mcp-per-server-router.md` 是 marker，6 个 per-server 文件是 `mcp-claude-browser/magic/openaiDeveloperDocs/sequential-thinking/supabase/kindly-web-search`。
- **声明了但 checked-in 正文未使用的占位符**：`agent-listing.removed`、`mcp-instructions.removed_names`、`local-command-caveat.tag_name`。三者**都是可用的**——是作者正文省略，不是 apply 不支持：
  - `agent-listing` 与 `mcp-instructions` 的 apply 用 `body.replace(/\$\{H\./g, …)`（L546 / L510）把任意 `${H.<prop>}` 统一改写到实际 delta 参数，所以 `{{removed}}` / `{{removed_names}}` 会正确展开（fixture P01/P02 验证）。
  - `local-command-caveat` 的 apply 在 L948 显式 `body.replace(/\$\{Gq_\}/g, '${'+tagVar+'}')`，`{{tag_name}}` 会展开为发现到的 tag 变量（fixture P03 验证）。
- **空正文的 5 个 suppression 文件**：`opened-file-in-ide.md`、`selected-lines-in-ide.md`、`token-usage.md`、`output-token-usage.md`、`mcp-kindly-web-search.md`。前四个是整条提醒静默（IDE 打开文件 / IDE 选区 / token telemetry / output-token telemetry），且它们的 `declared_placeholders` 一个都没用到。
- **空正文语义不统一**：per-server MCP 文件空 = 丢该 server 整块（`__tweakccMcpOverride` 返回 `null`）；marker 文件 `mcp-per-server-router.md` 空 = **关闭路由、回到 pristine**，不是删除；`local-command-caveat` 空 = 发 `content:""` 而不是 `[]`；`tool-result` 空 = 保留结果、去掉包装行。不能把「空 = 静默」外推到每个文件。这正是 [upstreams](upstreams.md) 里已点出的例外，本页把它落到具体函数。
- **`${{used}}` 货币前缀（fixture 验证）**：`budget-usd.md` 正文写作 `${{used}}` 而非 `{{used}}`；token 段替换为 `${H.used}`，前导字面 `$` 落在普通段被保留。[reminder-placeholders.mjs](../experiments/reminder-placeholders.mjs) 的 **P04** 直接执行了 `BUDGET_USD_INJECTION.apply` 并断言最终渲染为单一货币符号 `USD budget: $5/$10; $5 remaining`。所以该形态正确，**不要**判定为多余 `$` 或未替换。
- **dead override（归属：patch 作者注释）**：`verify-plan-reminder`。[apply L1415-1428](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/patches/systemReminderOverrides.ts#L1415-L1428) 的源码注释称 “CC 2.1.187 gutted the verify-plan reminder… survives only as a type label”；这是**patch 作者的声明**，本仓库未核验该 CC 版本事实。代码行为可确认的是：anchor 文本不存在时 apply 返回原 content（no-op），anchor 仍在但 shape 漂移时报错。作者正文另有可直接观察的缺陷：`Please call the "" tool directly` 引号内为空（应为工具名）。
- **shadow 声明**：16 个 reminder 文件的 frontmatter 带 `shadows:`，共 18 个目标 id；另有 5 个 registry 条目声明了硬编码 `injection.shadows`（单个条目可列多个 id）。18 个 frontmatter 目标中 16 个在 2.1.286 prompt catalog 中仍存在，作用是让 named-prompt pass 跳过这些 id；2 个不在 catalog：`edited-text-file.md` 声明的 `system-reminder-file-modification-detected-budget-exceeded`、`verify-plan-reminder.md` 声明的 `system-reminder-verify-plan-reminder`。**这两个缺失本身不构成当前 bug**：前者是 2.1.234 重命名前的**向后兼容别名**——[源码注释 L1032-1037](https://github.com/skrabe/tweakcc-fixed/blob/f3cf2d9978e209cea1383a0262fa5fc7089aea50/src/patches/systemReminderOverrides.ts#L1032-L1037) 说明 4 个 id 是为覆盖重命名前后两套名而一起列出，registry 里同时给了新名（`…diff-omitted-snippet-budget`、`…changed-since-read`，二者在 catalog 中存在）；comment 真正警告的是*新名*将来再次漂移时 stale id 不是惰性的（named-prompt pass 会迭代已被 splice 的区域），而不是“保留旧名=缺陷”。`verify-plan-reminder` 的 shadow 目标是作者注释所述被移除的 prompt。`systemPromptSync.loadShadowSet` 不校验 id 存在性。

## 逐文件摘要（完整字段见 JSON）

下面按「意图 → 实际 apply → 动态事实/占位符」压缩。行号均指 `src/patches/systemReminderOverrides.ts`。

**会话/环境类**

- `agent-listing.md`（`AGENT_LISTING_INJECTION` L521-555）：`findCaseBody('agent_listing_delta', 'Available agent types…')`；正文只留表头 + `{{listing}}`；`{{removed}}` 声明但正文未用（可接线，见上）。空 = `return []`。fixture P01 覆盖。
- `agent-mention.md`（L1323-1351）：key `agent_mention`；`${H.agentType}` 保留。空 = `=>[]`。
- `auto-mode-exit.md`（L1244-1290）：2.1.221+ 两臂，只替换非 `steerOnly` 分支，`bashFirst` 的 `${t}` 后缀保留、`steerOnly` 臂保持 pristine。空 = `=>[]`。
- `claudemd-context.md`（L361-425）：wrapper shape 匹配；正文里的 `Object.entries(_)` 会被改名成实际 ctx 参数；空 = `return msgs`（整 wrapper 短路）。
- `output-style-banner.md`（`OUTPUT_STYLE_INJECTION` L557-659）：保留前置 guards（2.1.238 的 type/empty 检查、256 上限、控制字符 sanitizer），只换 content 模板；`${_.name}` 走动态发现（2.1.238+ 是 `${pze(e.style)}`）。
- `thinking-reminder.md`（L661-685）、`ultrathink-effort.md`（L687-708）：无占位符，纯文案替换。
- `date-change.md`（L710-731）：`applySimpleEntry` + `${H.newDate}`。
- `stop-hook-session-goal.md`（L1704-1728）：`FN=(H)=>\`…\``；正文大幅加长反-作弊说明；空 = `FN=(H)=>""`。

**hooks**

- `hook-additional-context.md`（L733-763）、`hook-blocking-error.md`（L765-800）、`hook-stopped-continuation.md`（L802-828）：各自 `findAndReplace`，保留 hook 原文与字段；空 = `=>[]`。其中 blocking-error 的 suppression 被 registry 标为 DANGEROUS（模型看不到 hook 为何阻塞）。

**工具调用/结果**

- `tool-called.md`（L830-858）：空 = 发 `content:""`（下游 LW strip），非 `[]`；
- `tool-result.md`（L860-887）：空 = 保留结果、去包装行；
- `tool-error.md`（L889-915）：tool-result 的 catch 分支；REGISTRY 里 `TOOL_RESULT` 先于 `TOOL_ERROR`，两条作用于同一 region，改序会影响结果。
- `skills-listing.md`（`SKILLS_INJECTION` L427-478）：key `skill_listing`，`${H.content}` 保留；空 = `skill_listing:(H)=>{return [];}`。

**IDE / 本地执行**

- `local-command-caveat.md`（L917-954）：先按 `="local-command-caveat"` 定位 tag 变量；`tag_name` 由 L948 显式接线（fixture P03），正文未用；空 = `content:""`。
- `selected-lines-in-ide.md`（L1114-1166）：两种形态（2.1.186+ 直 arrow / ≤2.1.185 的 2000 字截断）；**正文为空 = 静默整个选区提醒**，4 个 declared 占位符未使用。
- `opened-file-in-ide.md`（L1168-1187）：**正文为空 = 静默**，`filename` 未使用。

**compact / plan / memory**

- `compact-file-reference.md`（L956-981）：`applySimpleEntry` + toolNameSlot（`${oO.name}` 或裸 `${Cs}`）。
- `pdf-reference.md`（L983-1013）：`applySimpleEntry`，支持 2.1.273 双分支 ternary（`matchComposedEntry`）；正文压掉原厂 MUST/Do NOT 段落。
- `edited-text-file.md`（L1015-1112）：2.1.234+ hoisted prefix 形态或旧双分支形态；正文把 snippet 空分支也并成同一模板。
- `plan-file-reference.md`（L1189-1216）、`plan-mode-exit.md`（L1218-1242）：分别保留 plan path/content、planExists 后缀；正文删去原厂条件式指引。
- `nested-memory.md`（L1292-1321）、`memory-update.md`（L1353-1397）：`memory-update` 用 `findCaseBody`，`${YT3[…].source}` 的 label map 变量动态发现（Mac `YT3` / linux-arm64 `Xj3`）；空 = `return []`。
- `verify-plan-reminder.md`（L1399-1446）：见上文 dead override。

**telemetry（空正文 suppression）**

- `token-usage.md`（L1448-1476）、`budget-usd.md`（L1478-1506）、`output-token-usage.md`（L1798-1828）：三者正文分别为空 / `${{…}}` / 空。`token-usage`、`output-token-usage` 的 declared 占位符均未使用且整条静默；`budget-usd` 的 `${{…}}` 端到端解析正确（见上）。

**任务/通知**

- `task-list-reminder.md`（L1508-1557）：`findCaseBody('task_reminder', …)` + `discoverFeatureGuard`（原样复用 feature gate）+ 现场生成 `q = H.content.map(…)`；正文的 `{{tasks}}` 先由 whitelist 转为 `${q}`，apply 再生成定义 q 的任务列表代码，两步共同提供运行值。
- `task-notification-framing.md`（L1559-1633）：2.1.205+ 只保留 framing var（message 由外部 `qUr` 追加），apply 会**删除**正文里的 `{{content}}`——若正文在 `{{content}}` 之后放文字，会跑到 message 之前。
- `user-sent-new-message.md`（L1635-1702）：2.1.286 hoist 成共享函数，human case 与 plugin `asUser` 路径同时受影响；旧形态用 case 前缀。
- `mcp-instructions.md`（L480-519）：整块表头；`removed_names` 声明但正文未用（可接线，fixture P02 覆盖）。

**MCP per-server**

- `mcp-per-server-router.md`（`MCP_PER_SERVER_ROUTER_INJECTION` L1730-1796）：匹配 assembly loop 的 **run-of-sets**（2.1.238 追加 baseline set），注入 `__tweakccMcpOverride` 运行时读 `~/.tweakcc/system-reminders/mcp-<name>.md`；空 body 返回 `null` → drop 该 server 块；含 `{{server_instructions}}` 则回填 pristine。**本文件空 = 关闭路由**。
- `mcp-claude-browser.md` / `mcp-magic.md` / `mcp-openaiDeveloperDocs.md` / `mcp-sequential-thinking.md`：正文即 `{{server_instructions}}`（等价 pristine）。
- `mcp-kindly-web-search.md`：空正文 = drop。
- `mcp-supabase.md`：完全替换，不使用 `{{server_instructions}}`（唯一明显改写 server 指令的 per-server 文件）。
- 这些文件只有在本机 `discoverMcpServerNames`（L1868-1887）读到同名 server 时才会被创建/同步，source-only 无法确认本机 server 名。

## 验证与后续

- **实际跑过的检查**：(a) 本页与 JSON 的 41 个文件清单以 `system-reminders/` 实测目录比对，JSON 经 `python3 -c json.load` 解析，文件集合与目录完全一致（0 缺 0 多）；(b) 逐文件 placeholder 由脚本比对；(c) 运行 [experiments/reminder-placeholders.mjs](../experiments/reminder-placeholders.mjs)（`node ... <checkout>`），P01–P05 全 PASS，Node v26.7.0——它在内存中执行纯 apply 函数 + 合成 bundle，未跑文件系统 apply driver、未装 CC、未发模型请求。未运行 `tweakcc-fixed` 的 build/test 或文件系统 apply driver。
- **未知/未验证**：`--apply` 在真实 2.1.286 安装上是否对每个 anchor 命中；fixture 只覆盖合成 bundle 形状（不证明任何已安装 build 可被 patch）；6 个 per-server 文件在目标机器是否存在同名 server；`shadows` 声明与 named-prompt pass 的完整交互（本页只读了 `loadShadowSet` 与注释）。verify-plan 的 2.1.187 移除属 patch 作者声明，未由本仓库核验。这些都需要另外安排隔离验证。
- **命名 prompt 家族（仅列出，供 coordinator 另案研究）**：`system-reminder-*`、`system-prompt-*`（如 exited-auto-mode、local-command-caveat）。本页不研究官方 Mods，也不涉及 `system-prompts-lcc` 正文。
