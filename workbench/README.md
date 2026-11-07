# CC Context Workbench

Claude Code 的本地问题工作台：从机制与做法进入同一案例的阶段、检查、请求原值与变更 brief。目标与职责见 [Context DevOps](../docs/context-devops.md)；它连接现有研究，不替代技术专题或生产 runtime。

## 生成与打开

需要 Python 3.10+，仅使用标准库。生成过程不调用 CC、模型或上游网络：

```sh
python3 scripts/build_context_atlas.py
```

产物是 `.cache/context-atlas/index.html` 与 `data.json`。直接用浏览器打开 HTML 即可，页面脚本、样式和数据已经内嵌，没有 CDN、字体下载、后端或服务依赖。默认目录位于 repo 内，文档链接相对返回本仓库；把 HTML 单独带走仍可交互，但 repo 文件链接需要相同的相对布局。

若浏览器不允许直接打开本地文件，可在 repo 根目录运行 `python3 -m http.server 8769 --bind 127.0.0.1`，打开 `http://127.0.0.1:8769/.cache/context-atlas/index.html`；这是临时静态预览，终端 `Ctrl-C` 停止。

`--out <local-output-directory>` 可选择本地输出位置；保持输出在 Git 外。`--data-only` 只生成研究数据，不组合界面。生成后，若 canonical docs/references 或 fixture 改动，重新运行同一个入口；页面是一个有日期的本地快照，没有后台自动更新。

## 从问题走到结果

默认打开「问题与做法」，选择 owned-core、dynamic-state 或 compact-resume。机制依据和步骤来自同一 [recipe 索引](../references/recipes.json)，三个固定合成案例均在 Python 端计算；「打开案例」接到「阶段与检查」，显式比较再接到「请求原值」，固定结果可带入「变更 brief」。案例有意含 FAIL；它不是一次未完成的导入。完整解释与 native 待执行方案见 [Handbook](../docs/handbook/index.md)。

也可直接 `python3 scripts/build_context_atlas.py --recipe dynamic-state`。`--recipe` 与 `--case` / `--run` / `--study` / `--capture` 互斥。显式导入仍优先打开对应视图；从问题页切入合成示例后，用「回到我带入的材料」恢复本页原始材料。切换仅选择预先生成的 bundle，不执行检查、不访问文件；已固定到 brief 的附件仍保留原值。A/B 研究是独立编辑空间，切换 recipe 不改写其 fixture、条件或未保存编辑；其视图明确标为独立研究，只有显式恢复 plan 才改变输入。

请求原值页的 A/B 选项随当前材料更新，包括 capture 数量相同的 recipe 切换。恢复的显式材料若没有 request captures，页面清空旧原值并禁用请求选择、观察导出与带入 brief；再次打开有请求的材料后恢复操作，已固定的 brief 附件不受影响。

「研究工具 +」展开 CC Run、对照研究、自主轮次回放、机制全景与来源；键盘方向键在当前可见 tabs 之间移动。关闭当前工具时回到问题页。完整学习入口与查看原值都无需网络。

Toolkit 也有统一入口，转交已有 canonical 脚本，不新增引擎：

```sh
python3 -m context_lab recipes
python3 -m context_lab workbench --recipe owned-core
python3 -m context_lab case case.json --out .cache/my-case
python3 -m context_lab inspect --help
python3 -m context_lab import-run --help
python3 -m context_lab study --help
python3 -m context_lab check
```

运行 recipe 的原始 case 时返回1表示有意保留的结构反例，2才是非法输入或IO错误；报告仍写出。检查模型行为与native运行需另按guide执行。

## 研究工具与材料动作

- **全景**：选择一个 context 环节，看来源/入口、owner、已有证据、关联问题和限制。图的箭头表达研究关系，不表示生产依赖自动扫描结果。
- **回放**：选择合成情境、trigger、placement 与 history，点击实际 wake 查看 current input、历史、排除原因和轮后 scripted results。主聊天的活跃窗口与一轮执行的 busy 窗口分别显示。
- **对照研究**：固定同一合成场景的 A/B 条件，逐来源检查 current/history/excluded/轮后产生，沿 constituent ID 查机会的跳过、延后与合并。保存完整 snapshot，导出报告或把研究固定带入 change brief。
- **研究案例**：固定同一问题、要求、合成 study 和多阶段 captures，按明确位置检查、查看失败/缺口，并作为完整 snapshot 带入 brief。
- **CC Run**：查看显式 selection 导入的请求及其 sidecar；未索引、响应关联冲突、partial scope 和未选引用保留，可重开固定 snapshot。
- **请求观察**：检查明确导入的 Anthropic Messages / OpenAI Responses body；条件、section 原值、未知字段与未展开引用并列显示。单份观察独立可用；同格式按 JSON pointer 比较，跨格式不自动配对。只准备明确 pair，缺少比较时导出选择再重建。默认合成案例的阶段 captures 不是 runtime 实测。
- **变更推演**：选择改动意图与范围，查看对应验证和原 runtime 交接问题，下载 Markdown brief。目标版本是填写的意图，不是实测结果。界面不执行展示的命令，不连接机器，不生成已激活配置。
- **来源**：检索本仓库 catalog 的已读上游 revision、阅读范围与已记录的新 tip；不会自动把 fetched tip 提升为已读 pin 或兼容版本。

## 数据与 authority

| Source | 拥有什么 |
| --- | --- |
| [model.json](model.json) | 人工整理的关系、运维问题、能力到相关检查的映射；结论链接回专题与 reference |
| [index.html](index.html)、[style.css](style.css)、[app.js](app.js) | 展示和交互；不拥有运行状态 |
| [build_context_atlas.py](../scripts/build_context_atlas.py) | 将现有 registry 与引擎结果投影成自包含页面 |
| `references/upstreams.json` | 已读来源 pin；更新情况按各条日期与范围解释 |
| `references/context-profile-compatibility.json` | 指定 candidate 的官方 offline 证据 |
| `references/target-runtime-2.1.289.json` | 独立本地 composition/types 观察 |
| [companion-input](../experiments/companion-input/README.md) | 合成规则、fixture 与回放引擎；Atlas 不复制一份模拟器 |
| [context_study.py](../experiments/companion-input/context_study.py) | plan 校验、canonical A/B 执行与逐来源观察投影；浏览器只展示投影，不模拟 |
| [cases.py](../context_lab/cases.py) | self-contained case、阶段关联、body pointer 检查与报告，复用 study/observer；不是独立 tracing |
| [observations.py](../context_lab/observations.py) | strict capture reader、证据层、原值投影与比较；浏览器使用同一 canonical 结果和原值文本 |
| [cc_runs.py](../context_lab/cc_runs.py)、[cc_run_view.py](../context_lab/cc_run_view.py) | 显式 CC 材料导入、关联与sidecar；固定snapshot重开和私有查看 |
| [io_policy.py](../context_lab/io_policy.py) | 各入口共享的 resolved 输出、每目标ignored/untracked检查；声明synthetic也不绕过 |
| [artifacts.py](../context_lab/artifacts.py) | Atlas 与报告 CLI 共用的预编码、输出预检与逐文件 atomic replace |

构建覆盖两个场景中全部六种 trigger × 三种 placement × 两种 history。所有合成选择和结果都是 fixture/规则的产物，不能用它们认定 CC/OpenClaw 或社区实现的自然行为。来源 archive、轮后结果和实际输入在回放中分开。

变更 brief 是下一次操作的准备材料。原 runtime repo 继续拥有真实 renderer、selector、启动方式和恢复；默认投影只含合成请求，不含真实私人配置。真实 capture 仅通过显式 `--capture` 进入本机 ignored 或 Git 外的 HTML/data/brief，绝不进入版本库；生产配置与私人 continuity 也不由页面接管。未经对应授权不安装、不启动 scheduler、不向外部 channel 发消息。

## CC run 与明确比较

完整的可运行例子与 selection 合同见 [CC runs](../docs/cc-runs.md)。`build_context_atlas.py --run run.json` 读取已导入的材料，或用 `--run cc-run-snapshot.json` 重开下载的固定包；不能与 `--case` / `--study` / `--capture` 混用。仅 importer 生成且 digest 匹配的同目录 captures 会被读取，原始日志引用不会被展开。

默认 run/capture 页不生成比较，B 为“单份观察”。`--pair A B`（可重复）或 `--pairs comparison-pairs.json` 明确准备有向 pair。case 默认使用自身声明的 pairs；需要别的组合时下载固定 case 输入及 pair 选择重建。未准备 pair 的页面会清空旧原值并禁用结果导出。正文和 canonical 显示材料按 capture 共享，pair 不再保存另一份完整正文；浏览器用 Python片段展开所选导出。

Run 页可按提交材料的 session/process/agent 分组；未知身份保持未记录，列表不冒充实际 tracing。选择请求后查看 scope、关联原记录，再跳到原值。run snapshot保存sidecar与captures；单份/pair导出携带sidecar和content losses，brief固定带入时的内容。原始response/index字节仍须保留源文件，snapshot不替代原始日志archive。

## 研究案例与重跑

「阶段与检查」展示当前案例：把同一个问题、保留要求、合成 study snapshot、多阶段 capture 和明确结构检查放在一起。可检查失败与缺口、选择阶段原值、跳到显式请求比较、恢复关联 study，并将完整报告固定带入 brief。JSON/Markdown 全部来自同次 Python 计算，浏览器不重新执行检查。

```sh
python3 scripts/run_context_case.py --demo --out .cache/context-case
python3 scripts/build_context_atlas.py --case .cache/context-case/case.json
```

合成示例有意保留 FAIL，runner 返回 1 并生成报告；缺材料、未检查的要求、模型行为与交付继续未评估。`--case` 内嵌 capture 同样只写 ignored 或 Git 外目录，不能与 --study/--capture 混用。下载 case 可重跑和重开，不自动保存；[完整合同](../docs/context-cases.md)。

## 对照研究与重跑

打开“对照研究”，选择研究起点或自行设置 A/B。原始问题和保留条件可编辑；条件只是一项声明，不是已经通过的检查。默认只改变一个轴，多轴会标为 compound。来源轨迹的不同表示这份合成材料下的输入差异，不给哪种配置更好打分。

“下载研究 JSON”保存完整 fixture snapshot，包含原话、来源元数据和两组条件。“下载对照 Markdown”保留已投影的实际轨迹及 plan；“带入变更 brief”固定当前研究作为附件，之后编辑研究不会静默修改已经带入的内容。

用同一个 canonical Python 引擎重跑：

```sh
python3 scripts/run_context_study.py plan.json --out .cache/context-study
```

得到 `plan.json`、`result.json`、`result.md`。输入 snapshot 固定不变；重跑仍使用当前引擎代码，不保证跨代码版本结果相同。详细合同与失败处理见 [STUDIES](../experiments/companion-input/STUDIES.md)。

页面“恢复保存的研究”可粘贴 plan JSON；未知字段、不可用条件或不一致的 fixture 会拒绝，保留当前工作。浏览器没有执行引擎，自定义/旧 snapshot 可用 builder 投影后再打开：

```sh
python3 scripts/build_context_atlas.py --study plan.json --out .cache/context-study/atlas
```

同名内置情境会在本次派生页面被 plan snapshot 替换；原 fixture 文件不变。新输出目录的文档相对链接需要 repo 的相对布局；页面交互本身不依赖这些链接。页面没有 localStorage 或自动保存，离开前下载 JSON；刷新会恢复生成时的 plan 或默认研究。

## 维护验证

私人请求观察的导入、输出与交接见 [request observation](../docs/request-observation.md)。`--capture` 可重复，只投影明确文件；输出必须留 Git 外或 ignored 目录。生成的 HTML/data/report 含完整输入，private remote 也不上传。页面不自动读取真实 logs 或服务端历史。

```sh
python3 scripts/test_io_policy.py
python3 scripts/test_cc_runs.py
python3 scripts/test_atlas_pairs.py
python3 scripts/test_cc_run_view.py
node --test scripts/test_run_ui.cjs
node --check workbench/runs.js
python3 scripts/test_build_context_atlas.py
python3 scripts/test_context_study.py
python3 scripts/test_context_cases.py
python3 scripts/test_context_case_atlas.py
node --test scripts/test_case_ui.cjs
node --check workbench/cases.js
python3 scripts/test_context_observations.py
python3 scripts/test_atlas_output_safety.py
python3 experiments/companion-input/run_lab.py --check --no-run
node --check workbench/app.js
node --check workbench/study.js
node --test scripts/test_study_ui.cjs
node --test scripts/test_observation_ui.cjs
node --check workbench/observations.js
```

构建器检查保护模型引用、控件与回放数据的接线、证据层级和 HTML 内数据的转义；已有 lab tests 拥有调度/保留规则。界面变化还要实际打开生成页面，检查全景选择、回放状态切换、A/B 来源轨迹、plan 恢复与失败、brief 下载、来源检索及桌面/窄屏布局。运行记录放 [current-state](../docs/current-state.md)，不要把“构建成功”写成界面或生产已验收。
