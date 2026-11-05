# Claude Code context 学习手册

这份 Handbook 把机制解释、固定合成材料与可重跑检查连成三条离线路径。Workbench 展示同一份 canonical Python 结果，Toolkit 脚本负责重跑。先读 [Context 来源地图](../context-map.md)，再按问题选择路径。它是一份有边界的学习手册，不是完整机制百科或可直接安装的 profile。

## 学习顺序与症状入口

| 路径 | 适合的问题 | 先分清什么 |
| --- | --- | --- |
| [Owned core 与工具保留](owned-core.md) | core 丢失，或 schema 还在但工具说明变了 | 主指导、工具名称、完整 input schema 与使用说明分别检查 |
| [动态 state、版本与纠正](dynamic-state.md) | 新 ambient 值出现，旧值仍在；纠正丢失或混淆 | 本轮新注入与历史记录分开；新值不自动改写旧 history |
| [Compact、resume 与部分证据](compact-resume.md) | summary 保留旧规则却丢纠正；resume 后仍用旧指导 | compact 投影、续接输入与 partial capture 的未知范围分别检查 |

如果终端看起来缺少 core，先定位 request 的 `/system`，不要从展示样式推断输入。工具仍可发现却用法不对时，结合 [官方控制面](../official-controls.md) 与 [Mods 迁移边界](../mods-migration.md)，分别观察 description、schema、实际调用和结果。跨窗后状态失真时，结合 [连续性与 Memory](../continuity-and-memory.md) 检查原话、summary 和重载来源。

## 重跑固定材料

在仓库根目录运行：

```sh
python3 scripts/run_context_case.py experiments/recipes/cases/owned-core.json --out .cache/recipe-owned-core
python3 scripts/run_context_case.py experiments/recipes/cases/dynamic-state.json --out .cache/recipe-dynamic-state
python3 scripts/run_context_case.py experiments/recipes/cases/compact-resume.json --out .cache/recipe-compact-resume
```

三个 runner 命令都预期返回 **1**：材料故意包含一个结构反例。成功写出 `case.json`、`report.json` 与 `report.md` 后发现 requirement 失败，才是这里的预期结果。退出 **2** 表示输入或 I/O 错误，不能当作预期反例。生成报告留在 ignored `.cache/`；修改源 case 后重跑，不手改报告。

对应的交互入口为：

```sh
python3 scripts/build_context_atlas.py --recipe owned-core --out .cache/cc-context-workbench
python3 scripts/build_context_atlas.py --recipe dynamic-state --out .cache/cc-context-workbench
python3 scripts/build_context_atlas.py --recipe compact-resume --out .cache/cc-context-workbench
```

打开输出目录的 `index.html`，查看阶段、原值、显式 comparisons 与检查。浏览器不重新计算检查，也不解析后重编码 request 原值。

## 怎样理解结果

`PASS` 表示该 `request_structure` requirement 的检查在已声明 scope 内满足；`FAIL` 表示至少一项检查不匹配，包括有意反例。`NOT_ASSESSED` 表示没有足够决定性证据，例如 capture 缺失、partial 字段未观察、pointer 被阻断、没有检查，或 requirement 属于 model behavior。

整体 case 的 FAIL 不代表 fixed 阶段修复失败：它可能来自保留下来的反例。读报告时按 stage、pointer、expected、actual 与 scope reason 定位。结果不是 readiness 分数；请求结构满足，也不能替代工具实际执行、模型理解或用户收到结果的证据。

机制旁的 source links 提供相关阅读依据；目前不是逐 claim 绑定的版本身份或 tracing 证明。合成阶段关系由作者声明，并非真实 Claude Code 生命周期。当前三条 recipe 的 native 层为 `NOT_ASSESSED`，下述采集协议为 `NOT_EXECUTED`；历史实测仍按原日期、build 与覆盖范围阅读。

## Native acquisition protocol

**状态：NOT_EXECUTED。** 以下是未来获得对应授权后的操作协议，不授予安装、native 会话、模型调用、网络、账号或生产变更权限。

1. 记录目标的 exact version 与 platform。历史基线是官方 `@anthropic-ai/claude-code-darwin-arm64@2.1.289` portable package，见 [兼容性记录](../../references/context-profile-compatibility.json) 与 [目标 runtime](../target-runtime.md)。它是该 build 的历史依据，不是当前安装指令。
2. 经目标 owner 批准的流程取得可信 binary。package、解包文件、原始输出和私人 request 留 Git 外。不要用文档版本代替 `--version` 的实际输出，也不要把当前 stable 版本填进未经验证的 recipe claim。
3. 执行 module 前先审阅它。用 `python3 scripts/check_context_profile.py --claude '<trusted-claude-executable>'` 运行官方离线检查；隔离条件、退出码与证据边界见 [升级检查流程](../maintenance.md#检查指定-cc-版本的-candidate)。validator 与非空 test kit 通过仍不是实际 request 或模型行为结果。
4. 只有另获本地 probe 授权后，才运行 `python3 scripts/probe_context_runtime.py --claude '<trusted-claude-executable>'`。它会启动隔离的本地 slash-command 会话，使用独立 `CLAUDE_CONFIG_DIR`、合成 key 与 loopback rejection endpoint；不是 no-session，也不使用真实 provider。具体条件见 [目标 runtime](../target-runtime.md)。根据目标生成的 declarations 检查能力，不臆造 flags 或 APIs。
5. 实际 request 的材料按官方 monitoring body-file 路径及 [CC run 导入合同](../cc-runs.md) 准备。只选已授权的合成或私人材料，原值保存在 Git 外或 ignored 路径，再用 `python3 scripts/import_cc_run.py --selection <selection.json> --out <private-output>` 显式导入。此步骤不扫描 logs、不跟随 capture 的路径、URL 或服务端引用，也不启用 provider 或发送 prompt。
6. 只有观察支持相应位置时，才把 recipe 的问题、要求、阶段与比较放入新的显式 case。采集及相关生命周期实际执行并记录前，`native_status` 保持 `NOT_ASSESSED`。分别记录 target types/composition、request、生命周期、模型行为与外部交付；未观察层保持未知。
