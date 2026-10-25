# context-profile：第一份候选 profile 的离线 candidate

状态：**未安装、未在模型会话中启用**的 source candidate。2026-10-05 已通过官方 Claude Code **2.1.289** 的 strict validation 和 offline test kit（3/3），另有 Node 合成测试（14/14）。官方 loader 已在 test kit 内加载本 module；随后本地 slash-command 会话也观察到真实 engine composition 中的 `lab:core`（见 [target runtime](../../docs/target-runtime.md)）。没有真实 HTTP request 或模型行为证据。它表达 profile 选定的一部分操作，不代表 C 组完整实现，合成 core 也不是最终身份。

## 它是什么 / 不是什么

- 是什么：一个 Mods 形状 hooks module，按**显式配置的 section name**、**engine-tier tool** 的 own-property 选择定点处理，外加一个合成 session core section。
- 公共 core 是合成文本（`lab:core`）；当前只验证源码逻辑与官方 offline 事件链。
- 没有安装入口：仓库不默认安装或启用。`plugin test` 的加载仅发生在测试进程内；真正用 `claude --plugin-dir <dir>` 启动会话及模型调用仍需对应授权。

## 目录

```
experiments/context-profile/
├── .claude-plugin/plugin.json   # 未安装候选的 manifest（version 0.0.0-uninstalled）
├── hooks/hooks.json             # modules: ./register.js
├── hooks/register.js            # 直接导出 register(on) + 配置 Maps + 合成 core
└── tests/
    ├── harness.js               # 合成 on/next 链，非官方 test kit
    ├── register.test.js         # 14 项 Node 窄验证
    └── official.test.ts         # 3 项官方 test kit 检查
```

## 表达的 profile 操作

唯一注册入口是直接导出的 `register(on)`。源码中的 `sectionOverrides` / `toolDescriptionOverrides`（Map）在注册时各取一份 snapshot；修改 authored Maps 后须重新加载 module。默认**选中 0 个 engine section**，追加合成 `lab:core`，并改写 engine/core 提供的 `Bash` description。这是未安装的 candidate 默认配置。

官方 2.1.289 的静态分析器拒绝了早先的 factory 导出 `register = createRegister()`；现已改成直接导出函数，Node 与官方 loader 共用这一条路径。不能用 Node tests 通过推定官方加载有效。

| 事件 | candidate 行为 | profile 合同 |
| --- | --- | --- |
| `prompt.section` | 按 `e.name` 在配置的 Map 中命中才替换；未配置/未知透传；core 已省略（`text===null`）保持省略 | 默认不选任何 engine section；原型名视作未知；不全局字串清洗 |
| `prompt.compose` | 把 `lab:core` **去重后放 shared/session 边界**（删同 id，再置于首个 session 前）；保留 engine sections 相对顺序与字段 | 私有 core 不得是 shared（跨组织缓存）；遵守 shared-before-session |
| `tool.describe` | 仅当 `e.provider` 是 engine/core 且 `e.tool` 命中才改 `description`；同名 foreign provider 透传；result 只含 `description`/`isDeferred?` | 工具 description 控制；不动 schema/权限/实现 |
| `prompt.attachment` | **未注册该事件**（无 handler） | 无 handler 即无改写；profile 明确不因 type/origin 就删载荷 |

未注册：`prompt.attachment`、`prompt.context`、`session.compact`（见 [profile design](../../docs/profile-design.md)）。candidate 不写占位 handler 冒充实现。

## 未证的选择器

`prompt.section` 的 `e.name` 是 engine 具名 section 名；官方 types 注释给出 `env_info_simple`、`memory` 等例子，**存在具名 section 不代表某段语义可改**。`doing_tasks` 无证据。测试只注入原创合成 selector `lab:synthetic-guidance`，验证机制，不推定任何真实 engine 段可改。`PromptComposeSection.id` 与 `PromptSectionInput.name` 是不同字段。

## 离线复现

```sh
node --test experiments/context-profile/tests/register.test.js
python3 scripts/check_context_profile.py --claude '<trusted-claude-executable>'
```

14 项检查（任一项被破坏，对应 test 应失败）：

1. 默认 production shape 选中 0 个 engine section（`env_info_simple`/`memory` 透传）。
2. 显式注入的合成 section：命中改写；`text:null` 保持 null；**其它 section 含同一 replacement 字符串时完整保真**；原型名视作未知。
3. `prompt.compose`：`lab:core` 是 `session` scope、位于 shared/session 边界；engine sections 顺序/字段保留；**重复渲染不重复**；`placeSessionSection` 对**第二个 session 位置**的已有同 id 做去重并移到边界（保留其它 session 相对顺序）。
4. `prompt.attachment`（candidate 未注册，测「无改写时」基线）：engine / settings-hook（`SessionStart`）/ plugin（`prompt.submit`）三种 origin 都保真。
5. `tool.describe`：engine-core Bash 命中时，**core 实际收到的 event** 除 `description` 外其余字段（`tool`/`isDeferred`/`provider`）保留、输入对象未被 mutate；`isDeferred=true` 与省略各保持原样；同名 foreign provider 保真。

第二条命令调用指定 CC 的官方 validator / test kit；不会下载 binary。3 项官方测试使用 `claude-code/testing`，在触发事件前显式 stub engine 答案，检查 session core 的位置与 engine sections 保真、engine/foreign tool description 的分流，以及未选中 section 的引文保真。composition 与 description 断言会拒绝 module 未加载的 no-op 结果。升级流程、状态和原始输出位置见 [maintenance](../../docs/maintenance.md#检查指定-cc-版本的-candidate)，本次便携证据见 [compatibility record](../../references/context-profile-compatibility.json)。

## 官方布局核对

- `.claude-plugin/plugin.json` 与 `hooks/hooks.json`（`modules: ["./register.js"]`）按官方 Mods reference 的目录布局表核对。
- 官方只说 hooks module 是 ES module，**未给 Node 最低版本**；本 candidate 不声明 Node 版本要求。

## 覆盖边界

- Node harness 是自行写的替身；官方 tests 证明 **2.1.289 test kit 的加载与合成事件链**。两者均不证明真实会话的 engine 默认内容、最终 request 或模型行为。
- 合成事件字段取自公开 types（`anthropics/claude-code@2bfb629d`，header 2.1.277），不证明目标 build 生成同样的类型。
- offline 命令未生成 `.claude-plugin/types/`；独立的本地命令探针现已生成 **2.1.289** 声明，已读具体 symbols 与版本差异见 [target runtime](../../docs/target-runtime.md)。官方描述的是目录加载时自动生成声明，见 [Create a mod](https://code.claude.com/docs/en/plugins/mods/create#get-type-definitions-for-your-version)。
- 未覆盖：真实 `prompt.attachment` 的 `detail`、nested instruction 后续加载、subagent/fork 继承、compact 重载、其它 model/模式的 engine sections、`todo_reminder` 到某 reminder 文件的对应。
