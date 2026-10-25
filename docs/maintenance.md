# 持续维护

更新方式：本地按需更新。当前没有 scheduler 或自动后台任务。每次 CC 升级、上游机制变化，或准备修改目标 runtime 配置时，从此页重新进入。

从 repo root 运行下面的只读命令即可比较十六个公开上游的 branch tip 与已读 revision。需要 Python 3.10+、Git 和 GitHub 网络访问，无新增 Python 依赖：

```sh
python3 scripts/check_upstreams.py
```

脚本只通过 `git ls-remote` 查询公开 refs，不更新 catalog、clone、安装或启动 Claude。退出码 `0` 表示全部未变，`1` 表示有新 revision 待阅读，`2` 表示至少一项未能查询；网络失败不会被当成“没有更新”。tip 未变也不代表目标 CC runtime 已兼容。

总 catalog 覆盖默认提示/reminder 的七个来源、Carryover/Pi/Cliff 的四个来源，以及 companion context 新增的五个来源。[Forge 详细 catalog](../references/forge-upstreams.json) 与 [Companion 详细 catalog](../references/companion-sources.json) 各自记录阅读和实验范围；总 catalog 的 revision 用于统一 refs 检查，变更已读 revision 时同步对应专题。Companion 对照共六项，其中 roof-mod 复用原有条目。历史线索表中尚未重新核读的仓库不自动加入 checker。

## 检查指定 CC 版本的 candidate

已审阅的 [context-profile](../experiments/context-profile/README.md) 有一条可复跑的官方 offline 检查入口。需要 Python 3.10+ 与自己选择的可信 CC 可执行文件，无新增 Python 依赖；脚本不获取最新版、不安装或 patch。从 repo root 运行：

```sh
python3 scripts/check_context_profile.py --claude '<trusted-claude-executable>'
```

也可以传 `--claude claude` 使用 PATH 中的 binary；报告记录它的实际路径和 `--version`，不会把文档版本当作被测版本。每次换版本后运行同一命令，比较报告中的版本、validator 诊断、测试计数与 types 状态。`--plugin` 可指定已审阅的另一 candidate，`--output` 可指定本地输出目录，`--timeout` 控制每条子命令秒数（默认 60）。输出必须在 plugin source 目录之外。自定义输出仍须留在 Git 外。

每次建立独立的 `.cache/context-profile-checks/run-*/`，保存干净 `candidate/`、空起点的 `config/` 与 `report.json`。复制时排除既有 `.claude-plugin/types/`，避免把上一版本声明误记为本次产物。依次执行：

1. `--version`：记录实际 build。
2. `plugin validate <candidate> --strict --json`：检查 manifest 和 hooks 静态分析；失败即停止。
3. `plugin test <candidate>`：由官方 loader 加载 module，以 synthetic engine stubs 测事件链；必须有正数 tests 通过、零失败，退出 0 却没有测试也不算成功。

报告保留执行时间、命令参数、stdout/stderr、退出码与分层状态。进程仅继承 PATH、固定 LANG 和所需隔离环境变量；指定独立 `CLAUDE_CONFIG_DIR`，关闭自动更新与非必要流量，不继承 API keys、provider/plugin/exporter 配置。它不是 OS sandbox，也不对未经阅读的 module 提供安全保证。官方描述这两个命令不启动 session、不登录、不联网；本次没有额外抓包证明。[Test a mod](https://code.claude.com/docs/en/plugins/mods/test)

| 退出码 / 字段 | 含义与下一步 |
| --- | --- |
| `0` / `offline_status=passed` | 本次 static validation 与非空官方 tests 通过；继续查看独立的 types/request/model 字段 |
| `1` / `failed` | candidate 校验或测试失败，包括空 suite；按保留的 diagnostics 修源码，再重跑 |
| `2` / `unsupported` | 目标命令或参数不支持；读该版本官方接口，不能自动改装 CC |
| `2` / `unavailable` | 找不到/不能执行 binary、超时或 hooks modules 被关闭；修调用条件，不能当作 candidate 已通过 |
| `2` / `unrecognized_output` | 版本、JSON 或测试输出格式不再可识别；先查原始输出，再按新官方格式修脚本 |
| `target_types=not_generated` | 当前命令没有生成目标声明，不借用旧 types 补成功 |
| `target_types=generated_not_reviewed` | 干净副本确有新 `.d.ts`，仅记录路径，仍须核对内容 |
| `request_behavior/model_behavior=not_tested` | 本入口始终不启动真实模型实验 |

找不到 binary 时返回退出 2 与简短 JSON，不建立 run 目录。其他已启动的检查报告都写入本地 run 目录；这不是通用跨版本兼容承诺，新的官方输出格式会明确留下未完成检查。

2026-10-05 实跑官方 `@anthropic-ai/claude-code-darwin-arm64@2.1.289`：strict validation 通过、官方 tests **3/3**，目标 types **未生成**。曾只在 Node 通过的 factory 导出被官方分析器拒绝，改成直接 `register(on)` 后才通过；这正是保留官方检查层的必要性。完整可移植结论见 [compatibility record](../references/context-profile-compatibility.json)。

官方说明目标 types 在 mod 目录加载/重载时自动写入 `.claude-plugin/types/`，不是一个已核实的 `/plugin-types` 命令。本轮 offline 命令没有产出它；为取声明而启动会话不属于脚本的自动 fallback。独立的 `python3 scripts/probe_context_runtime.py --claude <可信可执行文件>` 现已用本地 slash-command 会话完成目标声明与 composition 探针；它只连本机拒绝端点，具体条件和结果见 [target runtime](target-runtime.md)。[Create a mod](https://code.claude.com/docs/en/plugins/mods/create#get-type-definitions-for-your-version)

维护检查脚本与 authored module 时分别运行窄回归：

```sh
python3 scripts/test_check_context_profile.py
node --test experiments/context-profile/tests/register.test.js
```

脚本回归以 synthetic CLI 子进程验证通过/失败/空 suite/不支持/关闭/格式变化/超时/缺失 executable、旧 types 排除与环境隔离；不会调用真实模型或下载 binary。Node tests 不替代官方 loader 的验证。

## 一轮更新

1. 读 [current-state](current-state.md)，确认本轮需要解决的差异。
2. 查看 [upstream catalog](../references/upstreams.json) 的已读 revision，读取对应上游当前 revision；先看相关路径的变化，不自动更新安装。
3. 按 [official source list](../references/official-docs.json) 复核涉及的官方参数、事件和版本；有目标安装时对照其生成的 types，公开文档不能覆盖具体 build 的相反证据。
4. 更新同一份 [upstreams](upstreams.md)、[official controls](official-controls.md) 或对应主题，写清新结论是 source reading、作者声明还是实际实验。
5. 有行为规则变化时运行相关合成 fixture；真实模型和生产操作只在对应授权范围内进行。
6. 将当前结论修订回 current-state，保留有意义的历史 revision；私人机器定位与 handoff 在 Git 外更新。

上游代码可以缓存到被忽略的 `.cache/`，不要在本 repo 下执行它的 installer、patcher 或真实模型 tracer。研究笔记引用 exact commit 下的相关文件，避免未来 `main` 改变让旧结论失去上下文。

## 证据写法

- **文档确认**：明确参数或事件合同，附查阅日期和官方 URL。
- **源码确认**：附 repo revision 与 inspected path，只声称源码能够证明的行为。
- **离线验证**：写明合成输入与实际输出；不能外推兼容或模型行为。
- **真实 request / 行为验证**：写明目标版本、场景与结果；原始私人材料不入 Git。
- **未验证 / 待重新取回**：说明缺什么，保留下一条有用阅读路径。

不用一个笼统的“verified”覆盖全部层级。不按日期无限追加一套 current-state；同一结论变更回到它的权威页面。

## 发布边界

远端目前为 private，尚未选择公开 license。要公开发布时另行确定读者、材料范围和权利；private visibility 也不授权上传私人 reference log、外部 continuity、cache 或第三方全文。提交使用 explicit paths，并检查拟提交内容；真实实验和 VPS 操作继续按各自授权范围执行。
