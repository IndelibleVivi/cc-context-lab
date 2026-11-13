# 机制与证据索引

> 本页由 `python3 scripts/build_mechanism_evidence.py --write-handbook` 生成；修改 canonical catalog 或 renderer 后重建，不手改表格。

这份索引覆盖当前三条 recipe 使用的机制。claim IDs 连接具体判断与固定来源，相关阅读继续由 [Handbook](index.md) 和各专题拥有。它不是完整 CC 机制百科、真实 trace、跨阶段 receipt 或升级兼容性判定。来源版本与观察日期各自保留；固定一个历史 revision 不代表今天重新运行了那个 runtime。

Workbench 的「逐条判断与固定来源」和下载复用同一份 Python projection。可以在仓库根目录运行 `python3 -m context_lab evidence --recipe owned-core --format json` 查看对应 canonical 数据；将 `json` 换为 `markdown` 查看报告。

## 当前绑定一览

| Recipe | Mechanism ID | Claim IDs | Evidence levels |
| --- | --- | --- | --- |
| `owned-core` | `owned-core-boundary` | `claim-core-envelope-boundary`, `claim-core-2-1-289-composition`, `claim-core-native-unassessed` | `authored_source`, `historical_local_composition`, `unassessed` |
| `owned-core` | `tool-schema-guidance` | `claim-tool-description-boundary`, `claim-tool-schema-guidance-separate`, `claim-tool-schema-fixture`, `claim-tool-availability-unassessed` | `historical_target_types`, `authored_source`, `synthetic_fixture`, `unassessed` |
| `dynamic-state` | `revision-injection` | `claim-revision-supersession-layers`, `claim-revision-fixture-history`, `claim-revision-runtime-unassessed` | `authored_source`, `synthetic_fixture`, `unassessed` |
| `dynamic-state` | `correction-lineage` | `claim-correction-exact-position`, `claim-correction-fixture`, `claim-correction-target-types-boundary` | `authored_source`, `synthetic_fixture`, `unassessed` |
| `compact-resume` | `compact-retention` | `claim-compact-two-inputs`, `claim-compact-evidence-layering`, `claim-compact-correction-fixture`, `claim-compact-lifecycle-unassessed` | `historical_target_types`, `authored_source`, `synthetic_fixture`, `unassessed` |
| `compact-resume` | `resume-reload` | `claim-resume-reload-surface`, `claim-resume-preservation-criteria`, `claim-resume-fixture`, `claim-resume-actual-unassessed` | `official_documentation`, `authored_source`, `synthetic_fixture`, `unassessed` |
| `compact-resume` | `partial-absence` | `claim-partial-unobserved-different`, `claim-partial-fixture`, `claim-partial-absence-unassessed` | `authored_source`, `synthetic_fixture`, `unassessed` |

---

## Recipe mechanism evidence · owned-core

> 固定 source 与逐条判断的可追溯投影。层级保持原样；历史 source、合成 fixture、composition 与真实 request/lifecycle/model behavior 不因绑定而升级。

### 限制

- 本投影只绑定已记录的公开 source、合成 fixture 与历史观察；不证明当前平台或指定 CC build 仍具有相同行为。
- source inspection、target-types/composition 与真实 request、lifecycle、provider 呈现和模型行为是不同证据层。
- 三条 recipe 的 native_status 保持 NOT_ASSESSED；本投影不读取请求、不跟随 URL/路径引用、不执行模型或安装。
- 证据级别逐 claim 原样保留；不存在 readiness、兼容性或整体通过聚合。
- 离线校验检查当前 checkout 的 locator，以及声明 pin 的格式和 URL 一致性；不联网重取历史文件，不认证任意 claim 的语义。artifact revision 与所引用研究记录的 Git pin 分开阅读。

### Mechanisms

#### owned-core-boundary · Core 与工具声明的独立位置

System 与 tools 是不同输入面。一个位置保留完整，不足以证明另一个位置也完整，更不能证明模型已正确使用。

##### claim-core-envelope-boundary · `authored_source`

项目的请求模型将 system 指导、messages 与工具声明视为不同输入位置；一个位置完整，不能证明另一个也完整。

Sources: `owned-boundary-map`, `owned-boundary-profile`

- 这是项目自有的请求模型；本轮没有观察当前 CC 的真实请求。

##### claim-core-2-1-289-composition · `historical_local_composition`

2026-10-05 的单次本地 lean/print 2.1.289 composition 包含 scope 为 session 的 lab:core，位于 shared lean_body 之后。

Sources: `owned-boundary-runtime`

- 当时禁用了 tools、MCP、CLAUDE.md 和 auto-memory，只覆盖一个 model/prompt 分支。
- 未观察真实 provider 请求、HTTP body、生命周期转换或模型行为。

##### claim-core-native-unassessed · `unassessed`

固定目标 build 的真实请求是否保留该装配、模型是否采用指导，仍未评估。

Sources: `owned-boundary-runtime`

- 历史本地 composition 记录不能升级为 request 或行为结果。

##### Fixed sources

###### owned-boundary-map · Context 来源地图

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/context-map.md`
- locator: `{"heading":"按层研究","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-map.md
- 这是研究地图，不能证明某份请求包含图中的每种来源。

###### owned-boundary-profile · Profile 设计：独立输入面

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/profile-design.md`
- locator: `{"heading":"Profile 应能回答的事","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/profile-design.md
- 这里记录设计目标与未安装的 candidate，不是已部署 profile。

###### owned-boundary-runtime · 历史 CC 2.1.289 composition 观察

- kind: `target_runtime_artifact`
- revision: `@anthropic-ai/claude-code-darwin-arm64@2.1.289`
- observed on: `2026-10-05`
- path: `references/target-runtime-2.1.289.json`
- locator: `{"kind":"json_pointer","pointer":"/composition"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json
- 只覆盖历史 darwin-arm64 artifact；不声明当前平台或版本支持。
- 当时配置的 loopback endpoint 收到零请求。

#### tool-schema-guidance · 工具 schema 与使用指导分别验收

完整 input schema 和工具名可以仍在声明中，使用指导却已经丢失。发现、权限、执行和结果交付仍需独立观察。

##### claim-tool-description-boundary · `historical_target_types`

历史 2.1.289 记录列出选择性审阅过的 ToolDescribeInput、ToolDescribeResult 与 ToolDeferral；该记录不能证明真实工具执行。

Sources: `tool-schema-types`

- 只阅读了列出的目标声明，并未覆盖完整 declaration set。
- 工具 description 的改动范围与实际调用、权限和执行结果仍需分别验证。

##### claim-tool-schema-guidance-separate · `authored_source`

项目的迁移分析将工具 description 的改写责任与 schema、权限及工具结果保留分开。

Sources: `tool-schema-migration`

- 这是自有迁移约束；没有由此证明插件已安装或 runtime 行为已通过。

##### claim-tool-schema-fixture · `synthetic_fixture`

owned-core 的合成 stripped 阶段保留工具名、完整 input schema 与其他字段，同时刻意把一个工具的 description 设为 null。

Sources: `tool-schema-fixture`

- fixture 展示可重跑的结构对照，不是捕获的 CC 请求。

##### claim-tool-availability-unassessed · `unassessed`

三条 recipe 的真实工具可用性、权限、执行，以及模型是否遵循 description，均未评估。

Sources: `tool-schema-runtime-doc`

- 本轮没有进行 native 工具调用或目标模型会话。

##### Fixed sources

###### tool-schema-migration · Mods 迁移：工具 description 的责任

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/mods-migration.md`
- locator: `{"heading":"按入口迁移，不按文件名猜事件","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/mods-migration.md
- 迁移研究来自固定 types 与文档，没有安装 mod。

###### tool-schema-types · 历史 2.1.289 工具声明阅读记录

- kind: `target_runtime_artifact`
- revision: `@anthropic-ai/claude-code-darwin-arm64@2.1.289`
- observed on: `2026-10-05`
- path: `references/target-runtime-2.1.289.json`
- locator: `{"kind":"json_pointer","pointer":"/reviewed_symbols"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json
- 仅为单个历史 artifact 的选择性声明记录；声明形状不等于 runtime 执行。

###### tool-schema-fixture · Owned-core 合成工具/schema fixture

- kind: `synthetic_fixture`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `experiments/recipes/cases/owned-core.json`
- locator: `{"kind":"json_pointer","pointer":"/steps/1/capture/body/tools/0"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/owned-core.json
- 项目自有合成材料，不是 captured request。

###### tool-schema-runtime-doc · 历史目标 runtime 的限制记录

- kind: `target_runtime_artifact`
- revision: `@anthropic-ai/claude-code-darwin-arm64@2.1.289`
- observed on: `2026-10-05`
- path: `references/target-runtime-2.1.289.json`
- locator: `{"kind":"json_pointer","pointer":"/limits"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json
- 本轮没有重新获取或执行该 artifact。
- 记录覆盖选定声明和一次本地 composition，不包含请求或工具执行。


<details>
<summary>完整 canonical JSON 与序列化边界</summary>


```json
{
  "schema": "cc-context-recipe-evidence/1",
  "recipe_id": "owned-core",
  "mechanisms": [
    {
      "id": "owned-core-boundary",
      "title": "Core 与工具声明的独立位置",
      "explanation": "System 与 tools 是不同输入面。一个位置保留完整，不足以证明另一个位置也完整，更不能证明模型已正确使用。",
      "claims": [
        {
          "id": "claim-core-envelope-boundary",
          "statement": "项目的请求模型将 system 指导、messages 与工具声明视为不同输入位置；一个位置完整，不能证明另一个也完整。",
          "level": "authored_source",
          "source_ids": [
            "owned-boundary-map",
            "owned-boundary-profile"
          ],
          "limits": [
            "这是项目自有的请求模型；本轮没有观察当前 CC 的真实请求。"
          ]
        },
        {
          "id": "claim-core-2-1-289-composition",
          "statement": "2026-10-05 的单次本地 lean/print 2.1.289 composition 包含 scope 为 session 的 lab:core，位于 shared lean_body 之后。",
          "level": "historical_local_composition",
          "source_ids": [
            "owned-boundary-runtime"
          ],
          "limits": [
            "当时禁用了 tools、MCP、CLAUDE.md 和 auto-memory，只覆盖一个 model/prompt 分支。",
            "未观察真实 provider 请求、HTTP body、生命周期转换或模型行为。"
          ]
        },
        {
          "id": "claim-core-native-unassessed",
          "statement": "固定目标 build 的真实请求是否保留该装配、模型是否采用指导，仍未评估。",
          "level": "unassessed",
          "source_ids": [
            "owned-boundary-runtime"
          ],
          "limits": [
            "历史本地 composition 记录不能升级为 request 或行为结果。"
          ]
        }
      ]
    },
    {
      "id": "tool-schema-guidance",
      "title": "工具 schema 与使用指导分别验收",
      "explanation": "完整 input schema 和工具名可以仍在声明中，使用指导却已经丢失。发现、权限、执行和结果交付仍需独立观察。",
      "claims": [
        {
          "id": "claim-tool-description-boundary",
          "statement": "历史 2.1.289 记录列出选择性审阅过的 ToolDescribeInput、ToolDescribeResult 与 ToolDeferral；该记录不能证明真实工具执行。",
          "level": "historical_target_types",
          "source_ids": [
            "tool-schema-types"
          ],
          "limits": [
            "只阅读了列出的目标声明，并未覆盖完整 declaration set。",
            "工具 description 的改动范围与实际调用、权限和执行结果仍需分别验证。"
          ]
        },
        {
          "id": "claim-tool-schema-guidance-separate",
          "statement": "项目的迁移分析将工具 description 的改写责任与 schema、权限及工具结果保留分开。",
          "level": "authored_source",
          "source_ids": [
            "tool-schema-migration"
          ],
          "limits": [
            "这是自有迁移约束；没有由此证明插件已安装或 runtime 行为已通过。"
          ]
        },
        {
          "id": "claim-tool-schema-fixture",
          "statement": "owned-core 的合成 stripped 阶段保留工具名、完整 input schema 与其他字段，同时刻意把一个工具的 description 设为 null。",
          "level": "synthetic_fixture",
          "source_ids": [
            "tool-schema-fixture"
          ],
          "limits": [
            "fixture 展示可重跑的结构对照，不是捕获的 CC 请求。"
          ]
        },
        {
          "id": "claim-tool-availability-unassessed",
          "statement": "三条 recipe 的真实工具可用性、权限、执行，以及模型是否遵循 description，均未评估。",
          "level": "unassessed",
          "source_ids": [
            "tool-schema-runtime-doc"
          ],
          "limits": [
            "本轮没有进行 native 工具调用或目标模型会话。"
          ]
        }
      ]
    }
  ],
  "sources": [
    {
      "id": "owned-boundary-map",
      "title": "Context 来源地图",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/context-map.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "按层研究"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-map.md",
      "limits": [
        "这是研究地图，不能证明某份请求包含图中的每种来源。"
      ]
    },
    {
      "id": "owned-boundary-profile",
      "title": "Profile 设计：独立输入面",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/profile-design.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "Profile 应能回答的事"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/profile-design.md",
      "limits": [
        "这里记录设计目标与未安装的 candidate，不是已部署 profile。"
      ]
    },
    {
      "id": "owned-boundary-runtime",
      "title": "历史 CC 2.1.289 composition 观察",
      "kind": "target_runtime_artifact",
      "revision": "@anthropic-ai/claude-code-darwin-arm64@2.1.289",
      "observed_on": "2026-10-05",
      "path": "references/target-runtime-2.1.289.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/composition"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json",
      "limits": [
        "只覆盖历史 darwin-arm64 artifact；不声明当前平台或版本支持。",
        "当时配置的 loopback endpoint 收到零请求。"
      ]
    },
    {
      "id": "tool-schema-migration",
      "title": "Mods 迁移：工具 description 的责任",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/mods-migration.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "按入口迁移，不按文件名猜事件"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/mods-migration.md",
      "limits": [
        "迁移研究来自固定 types 与文档，没有安装 mod。"
      ]
    },
    {
      "id": "tool-schema-types",
      "title": "历史 2.1.289 工具声明阅读记录",
      "kind": "target_runtime_artifact",
      "revision": "@anthropic-ai/claude-code-darwin-arm64@2.1.289",
      "observed_on": "2026-10-05",
      "path": "references/target-runtime-2.1.289.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/reviewed_symbols"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json",
      "limits": [
        "仅为单个历史 artifact 的选择性声明记录；声明形状不等于 runtime 执行。"
      ]
    },
    {
      "id": "tool-schema-fixture",
      "title": "Owned-core 合成工具/schema fixture",
      "kind": "synthetic_fixture",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "experiments/recipes/cases/owned-core.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/steps/1/capture/body/tools/0"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/owned-core.json",
      "limits": [
        "项目自有合成材料，不是 captured request。"
      ]
    },
    {
      "id": "tool-schema-runtime-doc",
      "title": "历史目标 runtime 的限制记录",
      "kind": "target_runtime_artifact",
      "revision": "@anthropic-ai/claude-code-darwin-arm64@2.1.289",
      "observed_on": "2026-10-05",
      "path": "references/target-runtime-2.1.289.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/limits"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json",
      "limits": [
        "本轮没有重新获取或执行该 artifact。",
        "记录覆盖选定声明和一次本地 composition，不包含请求或工具执行。"
      ]
    }
  ],
  "caveats": [
    "本投影只绑定已记录的公开 source、合成 fixture 与历史观察；不证明当前平台或指定 CC build 仍具有相同行为。",
    "source inspection、target-types/composition 与真实 request、lifecycle、provider 呈现和模型行为是不同证据层。",
    "三条 recipe 的 native_status 保持 NOT_ASSESSED；本投影不读取请求、不跟随 URL/路径引用、不执行模型或安装。",
    "证据级别逐 claim 原样保留；不存在 readiness、兼容性或整体通过聚合。",
    "离线校验检查当前 checkout 的 locator，以及声明 pin 的格式和 URL 一致性；不联网重取历史文件，不认证任意 claim 的语义。artifact revision 与所引用研究记录的 Git pin 分开阅读。"
  ]
}
```

以上 JSON 是同一 projection 的 canonical 序列化。验证只读取固定 repo-relative 文件与声明 locator，不跟随 URL、material reference、request 路径或 runtime 状态。

</details>

---

## Recipe mechanism evidence · dynamic-state

> 固定 source 与逐条判断的可追溯投影。层级保持原样；历史 source、合成 fixture、composition 与真实 request/lifecycle/model behavior 不因绑定而升级。

### 限制

- 本投影只绑定已记录的公开 source、合成 fixture 与历史观察；不证明当前平台或指定 CC build 仍具有相同行为。
- source inspection、target-types/composition 与真实 request、lifecycle、provider 呈现和模型行为是不同证据层。
- 三条 recipe 的 native_status 保持 NOT_ASSESSED；本投影不读取请求、不跟随 URL/路径引用、不执行模型或安装。
- 证据级别逐 claim 原样保留；不存在 readiness、兼容性或整体通过聚合。
- 离线校验检查当前 checkout 的 locator，以及声明 pin 的格式和 URL 一致性；不联网重取历史文件，不认证任意 claim 的语义。artifact revision 与所引用研究记录的 Git pin 分开阅读。

### Mechanisms

#### revision-injection · 新注入与历史保留分别检查

新快照能明确本轮采用的 revision；旧快照仍可能在 messages 历史中。需要逐位置核对，不能只看最新注入包。

##### claim-revision-supersession-layers · `authored_source`

替换本轮新注入的 current state，与移除已在对话历史中的旧值，是不同操作，也需要不同证据。

Sources: `revision-retention`, `revision-continuity`

- 这是保留合同；它不能识别真实 producer，也不能证明注入时机。

##### claim-revision-fixture-history · `synthetic_fixture`

dynamic-state 的合成 fixed 阶段追加 revision 3，并在固定 messages 位置保留 revision 1 和 revision 2。

Sources: `revision-fixture`

- message roles 与位置由作者构造，不能据此证明真实来源或 current-state 语义。

##### claim-revision-runtime-unassessed · `unassessed`

实际注入时间、旧值退出 current 的时机、resume 行为和模型对新状态的采用仍未评估。

Sources: `revision-observation`

- case engine 只检查 snapshot 中显式提供的 request-body 位置。

##### Fixed sources

###### revision-retention · Context 保留的不同操作面

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/context-retention.md`
- locator: `{"heading":"先说明什么已经“读过”","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-retention.md
- 该页区分下一次注入、当前 request、transcript 与 archive，没有声称这些面都已观察。

###### revision-continuity · 连续性与 Memory 的职责面

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/continuity-and-memory.md`
- locator: `{"heading":"一个研究范围，几个不同的操作","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/continuity-and-memory.md
- 这是责任模型，没有安装或运行 context manager。

###### revision-fixture · Dynamic-state 合成 revision fixture

- kind: `synthetic_fixture`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `experiments/recipes/cases/dynamic-state.json`
- locator: `{"kind":"json_pointer","pointer":"/steps/3/capture/body/messages"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/dynamic-state.json
- 仅为合成 messages，没有 runtime provenance 或模型后续行为。

###### revision-observation · 请求观察的范围

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/request-observation.md`
- locator: `{"heading":"投影与比较的精确边界","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/request-observation.md
- 本地 observer 报告位置和值；origin 与 lifecycle 保持 unknown。

#### correction-lineage · 保留纠正的原文与关联

纠正要能与被纠正的状态区分。结构位置中出现纠正，只证明材料存在，模型是否采用新值仍未评估。

##### claim-correction-exact-position · `authored_source`

纠正原文与被纠正的状态需要在显式位置保持可区分，才能检查保留关系。

Sources: `correction-cases-doc`, `correction-companion`

- 这是自有保留要求，不能证明模型采用了较新的指令。

##### claim-correction-fixture · `synthetic_fixture`

合成 fixed 阶段在旧状态之后，用独立 message 保留精确的纠正原文。

Sources: `correction-fixture`

- 阶段关系由 fixture 作者声明，不是 live session tracing。

##### claim-correction-target-types-boundary · `unassessed`

历史 2.1.289 类型与 composition 观察不能证明真实生命周期保留了纠正，也不能证明模型采用了纠正。

Sources: `correction-target`

- 所引 artifact 记录只有选定声明与 composition metadata，没有对话行为结果。

##### Fixed sources

###### correction-cases-doc · Context case 的请求位置合同

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/context-cases.md`
- locator: `{"heading":"输入合同","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-cases.md
- 检查只证明提供材料中选定 request-body 位置的值。

###### correction-companion · 伴侣 context 的保留问题

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/companion-context.md`
- locator: `{"heading":"纳入什么","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/companion-context.md
- 这里定义研究范围；本仓库没有由此部署 companion runtime。

###### correction-fixture · 合成纠正 fixture

- kind: `synthetic_fixture`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `experiments/recipes/cases/dynamic-state.json`
- locator: `{"kind":"json_pointer","pointer":"/steps/3/capture/body/messages/3"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/dynamic-state.json
- 合成内容不能认证真实纠正来源，也不能证明后续采用。

###### correction-target · 历史目标 runtime 的 composition 限制

- kind: `target_runtime_artifact`
- revision: `@anthropic-ai/claude-code-darwin-arm64@2.1.289`
- observed on: `2026-10-05`
- path: `references/target-runtime-2.1.289.json`
- locator: `{"kind":"json_pointer","pointer":"/limits"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json
- 保留历史 artifact 与日期；本轮没有重新研究或验证当前能力。


<details>
<summary>完整 canonical JSON 与序列化边界</summary>


```json
{
  "schema": "cc-context-recipe-evidence/1",
  "recipe_id": "dynamic-state",
  "mechanisms": [
    {
      "id": "revision-injection",
      "title": "新注入与历史保留分别检查",
      "explanation": "新快照能明确本轮采用的 revision；旧快照仍可能在 messages 历史中。需要逐位置核对，不能只看最新注入包。",
      "claims": [
        {
          "id": "claim-revision-supersession-layers",
          "statement": "替换本轮新注入的 current state，与移除已在对话历史中的旧值，是不同操作，也需要不同证据。",
          "level": "authored_source",
          "source_ids": [
            "revision-retention",
            "revision-continuity"
          ],
          "limits": [
            "这是保留合同；它不能识别真实 producer，也不能证明注入时机。"
          ]
        },
        {
          "id": "claim-revision-fixture-history",
          "statement": "dynamic-state 的合成 fixed 阶段追加 revision 3，并在固定 messages 位置保留 revision 1 和 revision 2。",
          "level": "synthetic_fixture",
          "source_ids": [
            "revision-fixture"
          ],
          "limits": [
            "message roles 与位置由作者构造，不能据此证明真实来源或 current-state 语义。"
          ]
        },
        {
          "id": "claim-revision-runtime-unassessed",
          "statement": "实际注入时间、旧值退出 current 的时机、resume 行为和模型对新状态的采用仍未评估。",
          "level": "unassessed",
          "source_ids": [
            "revision-observation"
          ],
          "limits": [
            "case engine 只检查 snapshot 中显式提供的 request-body 位置。"
          ]
        }
      ]
    },
    {
      "id": "correction-lineage",
      "title": "保留纠正的原文与关联",
      "explanation": "纠正要能与被纠正的状态区分。结构位置中出现纠正，只证明材料存在，模型是否采用新值仍未评估。",
      "claims": [
        {
          "id": "claim-correction-exact-position",
          "statement": "纠正原文与被纠正的状态需要在显式位置保持可区分，才能检查保留关系。",
          "level": "authored_source",
          "source_ids": [
            "correction-cases-doc",
            "correction-companion"
          ],
          "limits": [
            "这是自有保留要求，不能证明模型采用了较新的指令。"
          ]
        },
        {
          "id": "claim-correction-fixture",
          "statement": "合成 fixed 阶段在旧状态之后，用独立 message 保留精确的纠正原文。",
          "level": "synthetic_fixture",
          "source_ids": [
            "correction-fixture"
          ],
          "limits": [
            "阶段关系由 fixture 作者声明，不是 live session tracing。"
          ]
        },
        {
          "id": "claim-correction-target-types-boundary",
          "statement": "历史 2.1.289 类型与 composition 观察不能证明真实生命周期保留了纠正，也不能证明模型采用了纠正。",
          "level": "unassessed",
          "source_ids": [
            "correction-target"
          ],
          "limits": [
            "所引 artifact 记录只有选定声明与 composition metadata，没有对话行为结果。"
          ]
        }
      ]
    }
  ],
  "sources": [
    {
      "id": "revision-retention",
      "title": "Context 保留的不同操作面",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/context-retention.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "先说明什么已经“读过”"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-retention.md",
      "limits": [
        "该页区分下一次注入、当前 request、transcript 与 archive，没有声称这些面都已观察。"
      ]
    },
    {
      "id": "revision-continuity",
      "title": "连续性与 Memory 的职责面",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/continuity-and-memory.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "一个研究范围，几个不同的操作"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/continuity-and-memory.md",
      "limits": [
        "这是责任模型，没有安装或运行 context manager。"
      ]
    },
    {
      "id": "revision-fixture",
      "title": "Dynamic-state 合成 revision fixture",
      "kind": "synthetic_fixture",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "experiments/recipes/cases/dynamic-state.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/steps/3/capture/body/messages"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/dynamic-state.json",
      "limits": [
        "仅为合成 messages，没有 runtime provenance 或模型后续行为。"
      ]
    },
    {
      "id": "revision-observation",
      "title": "请求观察的范围",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/request-observation.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "投影与比较的精确边界"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/request-observation.md",
      "limits": [
        "本地 observer 报告位置和值；origin 与 lifecycle 保持 unknown。"
      ]
    },
    {
      "id": "correction-cases-doc",
      "title": "Context case 的请求位置合同",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/context-cases.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "输入合同"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-cases.md",
      "limits": [
        "检查只证明提供材料中选定 request-body 位置的值。"
      ]
    },
    {
      "id": "correction-companion",
      "title": "伴侣 context 的保留问题",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/companion-context.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "纳入什么"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/companion-context.md",
      "limits": [
        "这里定义研究范围；本仓库没有由此部署 companion runtime。"
      ]
    },
    {
      "id": "correction-fixture",
      "title": "合成纠正 fixture",
      "kind": "synthetic_fixture",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "experiments/recipes/cases/dynamic-state.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/steps/3/capture/body/messages/3"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/dynamic-state.json",
      "limits": [
        "合成内容不能认证真实纠正来源，也不能证明后续采用。"
      ]
    },
    {
      "id": "correction-target",
      "title": "历史目标 runtime 的 composition 限制",
      "kind": "target_runtime_artifact",
      "revision": "@anthropic-ai/claude-code-darwin-arm64@2.1.289",
      "observed_on": "2026-10-05",
      "path": "references/target-runtime-2.1.289.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/limits"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json",
      "limits": [
        "保留历史 artifact 与日期；本轮没有重新研究或验证当前能力。"
      ]
    }
  ],
  "caveats": [
    "本投影只绑定已记录的公开 source、合成 fixture 与历史观察；不证明当前平台或指定 CC build 仍具有相同行为。",
    "source inspection、target-types/composition 与真实 request、lifecycle、provider 呈现和模型行为是不同证据层。",
    "三条 recipe 的 native_status 保持 NOT_ASSESSED；本投影不读取请求、不跟随 URL/路径引用、不执行模型或安装。",
    "证据级别逐 claim 原样保留；不存在 readiness、兼容性或整体通过聚合。",
    "离线校验检查当前 checkout 的 locator，以及声明 pin 的格式和 URL 一致性；不联网重取历史文件，不认证任意 claim 的语义。artifact revision 与所引用研究记录的 Git pin 分开阅读。"
  ]
}
```

以上 JSON 是同一 projection 的 canonical 序列化。验证只读取固定 repo-relative 文件与声明 locator，不跟随 URL、material reference、request 路径或 runtime 状态。

</details>

---

## Recipe mechanism evidence · compact-resume

> 固定 source 与逐条判断的可追溯投影。层级保持原样；历史 source、合成 fixture、composition 与真实 request/lifecycle/model behavior 不因绑定而升级。

### 限制

- 本投影只绑定已记录的公开 source、合成 fixture 与历史观察；不证明当前平台或指定 CC build 仍具有相同行为。
- source inspection、target-types/composition 与真实 request、lifecycle、provider 呈现和模型行为是不同证据层。
- 三条 recipe 的 native_status 保持 NOT_ASSESSED；本投影不读取请求、不跟随 URL/路径引用、不执行模型或安装。
- 证据级别逐 claim 原样保留；不存在 readiness、兼容性或整体通过聚合。
- 离线校验检查当前 checkout 的 locator，以及声明 pin 的格式和 URL 一致性；不联网重取历史文件，不认证任意 claim 的语义。artifact revision 与所引用研究记录的 Git pin 分开阅读。

### Mechanisms

#### compact-retention · 摘要投影与信息损失

摘要可能保留早期指导，却省略后来的纠正。两者要分别检查，语义使用留给后续验收。

##### claim-compact-two-inputs · `historical_target_types`

保留的 2.1.289 观察记录列出 compact 输入的 trigger、可选 agentId/instructions 和 messages，输出记为 SessionCompacted | SessionCompactSkipped。

Sources: `compact-types`

- 这些字段来自 2026-10-05 对目标 artifact 的选择性阅读记录。
- 没有执行 compact，也未证明所有内部摘要路径都受该入口覆盖。

##### claim-compact-evidence-layering · `authored_source`

项目的 compact 分析分别保留文档、公开 types、目标 types 与实际 runtime 四层证据。

Sources: `compact-doc`, `compact-types-doc`

- 这是研究分层合同，不能证明 compaction 实际执行。
- 目标 build 的历史报告仍保留原日期；引用它的项目文件有独立 Git pin。

##### claim-compact-correction-fixture · `synthetic_fixture`

合成 compacted_stale 阶段刻意省略稍后的精确纠正，同时保留更早的指导。

Sources: `compact-fixture`

- 这是作者构造的反例，不是捕获的 compaction 结果。

##### claim-compact-lifecycle-unassessed · `unassessed`

真实 automatic/manual compact 的执行、摘要内容、装回的 messages 和后续 request 仍未评估。

Sources: `compact-types`

- 声明结构和单个合成情境不能证明生命周期行为。

##### Fixed sources

###### compact-doc · Compact 控制的证据分层

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/compact-control.md`
- locator: `{"heading":"四层证据必须分开","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/compact-control.md
- 该页明确记录 compact runtime 层尚未观察。

###### compact-types · 历史 2.1.289 compact 字段记录

- kind: `target_runtime_artifact`
- revision: `@anthropic-ai/claude-code-darwin-arm64@2.1.289`
- observed on: `2026-10-05`
- path: `references/target-runtime-2.1.289.json`
- locator: `{"kind":"json_pointer","pointer":"/findings"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json
- 该 locator 指向保留报告中的字段与 union 记录，不是完整 declaration diff。
- 历史 target types 不能证明事件执行。

###### compact-fixture · 合成有损摘要 fixture

- kind: `synthetic_fixture`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `experiments/recipes/cases/compact-resume.json`
- locator: `{"kind":"json_pointer","pointer":"/steps/1/capture/body/messages"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/compact-resume.json
- 摘要和省略都由作者构造为合成输入。

###### compact-types-doc · 历史目标 build 的项目报告

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-10-05`
- path: `docs/target-runtime.md`
- locator: `{"heading":"目标类型带来的修订","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/target-runtime.md
- 该页记录保留 artifact 的研究结果，不是新一轮平台观察。

#### resume-reload · 恢复后的输入独立核对

续接提示可以存在，旧的错误指导也可能仍然存在。需要分别观察摘要与恢复后的实际请求。

##### claim-resume-reload-surface · `official_documentation`

2026-10-05 的官方文档覆盖记录包含 PreCompact、PostCompact、SessionStart 与 context 注入及 resume 重放主题；记录明确为 runtime_verified=false。

Sources: `resume-official-docs`, `resume-controls`

- 这里引用固定的研究记录，不声明官网有对应版本快照，也不能证明当前 build 或配置实际执行了这些路径。

##### claim-resume-preservation-criteria · `authored_source`

项目的 handoff 要求跨生命周期核对纠正、近期原话、来源身份与恢复状态。

Sources: `resume-continuity`

- 这些是 candidate 的保留要求，不能证明一次 resume 已满足它们。

##### claim-resume-fixture · `synthetic_fixture`

合成 fixed 阶段包含明确标记的 continuation prompt；partial 阶段仅包含已声明观察的 model/system/tools。

Sources: `resume-fixture`

- 字面的 resume 提示不能证明执行过 resume 或成功 reload。

##### claim-resume-actual-unassessed · `unassessed`

真实 resume/continue 的输入装配、重载来源、轮次关系和模型行为仍未评估。

Sources: `resume-map`

- 本轮没有执行 native resume、compact 或 provider 请求。

##### Fixed sources

###### resume-controls · 官方控制面的历史研究记录

- kind: `official_documentation_report`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-10-05`
- path: `docs/official-controls.md`
- locator: `{"heading":"官方控制面核对","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/official-controls.md
- 仅阅读选定官方段落，没有保存官网全站快照。
- Git revision 固定本项目的报告，不是官网文档版本。

###### resume-official-docs · Hooks 文档的历史覆盖记录

- kind: `official_documentation_report`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-10-05`
- path: `references/official-docs.json`
- locator: `{"kind":"json_pointer","pointer":"/sources/10"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/official-docs.json
- 该记录包含选定 hook、compact/reload 与 resume 重放主题，runtime_verified=false。
- Git pin 固定覆盖记录；官网原 URL 不作为不可变版本，本轮没有重新抓取该页面。

###### resume-continuity · 连续性 handoff 要求

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/continuity-and-memory.md`
- locator: `{"heading":"Handoff 要保住的内容","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/continuity-and-memory.md
- 这是 candidate 保留判据，不是已部署的 reload 实现。

###### resume-fixture · 合成 compact/resume fixture

- kind: `synthetic_fixture`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `experiments/recipes/cases/compact-resume.json`
- locator: `{"kind":"json_pointer","pointer":"/steps/2/capture/body/messages/3"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/compact-resume.json
- continuation 提示是合成文本。

###### resume-map · Context 地图的生命周期边界

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/context-map.md`
- locator: `{"heading":"改写时保留什么","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-map.md
- 该地图要求独立生命周期证据，本身不能替代该证据。

#### partial-absence · 未观察字段保持未知

只观察 system/tools 的 capture 无法判断 messages 是否已退出；不能把未观察当成已删除。

##### claim-partial-unobserved-different · `authored_source`

对于 partial request body，未观察到某个顶层字段，不构成该字段已缺失的证据。

Sources: `partial-contract`, `partial-code`, `partial-cases`

- 合同只覆盖明确提供给本地工具的材料，不能证明 provider 或服务端历史。

##### claim-partial-fixture · `synthetic_fixture`

合成 partial 阶段声明 model/system/tools，并同时从 body 和 observed-field 清单中省略 messages。

Sources: `partial-fixture`

- 这是声明的部分观察形状，不能推成真实请求没有 messages。

##### claim-partial-absence-unassessed · `unassessed`

这份 partial capture 无法判断 messages、服务端注入的 context 或模型后续可见内容是否缺失。

Sources: `partial-code`

- 实现保留 unknown scope，不从未观察推断 absence。

##### Fixed sources

###### partial-contract · 请求观察的 partial scope 合同

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/request-observation.md`
- locator: `{"heading":"部分 request body：只声明观察到的顶层字段","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/request-observation.md
- 合同描述导入材料，不认证 native provenance。

###### partial-code · Partial evidence-scope 实现

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `context_lab/observations.py`
- locator: `{"kind":"python_symbol","symbol":"_evidence_scope"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/context_lab/observations.py
- 源码存在和本地测试不认证 native capture format。

###### partial-cases · Case pointer 与 partial-scope 行为

- kind: `authored_source`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `docs/context-cases.md`
- locator: `{"heading":"输入合同","kind":"markdown_heading"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-cases.md
- 规则仅适用于显式提供 case 的 body 位置。

###### partial-fixture · 合成 partial system/tools capture

- kind: `synthetic_fixture`
- revision: `34bc41ae80c0f5f2047b1cc272dd1663d4569a9c`
- observed on: `2026-11-13`
- path: `experiments/recipes/cases/compact-resume.json`
- locator: `{"kind":"json_pointer","pointer":"/steps/3/capture/evidence_scope"}`
- url: https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/compact-resume.json
- manifest 声明是合成材料，不能认证 capture。


<details>
<summary>完整 canonical JSON 与序列化边界</summary>


```json
{
  "schema": "cc-context-recipe-evidence/1",
  "recipe_id": "compact-resume",
  "mechanisms": [
    {
      "id": "compact-retention",
      "title": "摘要投影与信息损失",
      "explanation": "摘要可能保留早期指导，却省略后来的纠正。两者要分别检查，语义使用留给后续验收。",
      "claims": [
        {
          "id": "claim-compact-two-inputs",
          "statement": "保留的 2.1.289 观察记录列出 compact 输入的 trigger、可选 agentId/instructions 和 messages，输出记为 SessionCompacted | SessionCompactSkipped。",
          "level": "historical_target_types",
          "source_ids": [
            "compact-types"
          ],
          "limits": [
            "这些字段来自 2026-10-05 对目标 artifact 的选择性阅读记录。",
            "没有执行 compact，也未证明所有内部摘要路径都受该入口覆盖。"
          ]
        },
        {
          "id": "claim-compact-evidence-layering",
          "statement": "项目的 compact 分析分别保留文档、公开 types、目标 types 与实际 runtime 四层证据。",
          "level": "authored_source",
          "source_ids": [
            "compact-doc",
            "compact-types-doc"
          ],
          "limits": [
            "这是研究分层合同，不能证明 compaction 实际执行。",
            "目标 build 的历史报告仍保留原日期；引用它的项目文件有独立 Git pin。"
          ]
        },
        {
          "id": "claim-compact-correction-fixture",
          "statement": "合成 compacted_stale 阶段刻意省略稍后的精确纠正，同时保留更早的指导。",
          "level": "synthetic_fixture",
          "source_ids": [
            "compact-fixture"
          ],
          "limits": [
            "这是作者构造的反例，不是捕获的 compaction 结果。"
          ]
        },
        {
          "id": "claim-compact-lifecycle-unassessed",
          "statement": "真实 automatic/manual compact 的执行、摘要内容、装回的 messages 和后续 request 仍未评估。",
          "level": "unassessed",
          "source_ids": [
            "compact-types"
          ],
          "limits": [
            "声明结构和单个合成情境不能证明生命周期行为。"
          ]
        }
      ]
    },
    {
      "id": "resume-reload",
      "title": "恢复后的输入独立核对",
      "explanation": "续接提示可以存在，旧的错误指导也可能仍然存在。需要分别观察摘要与恢复后的实际请求。",
      "claims": [
        {
          "id": "claim-resume-reload-surface",
          "statement": "2026-10-05 的官方文档覆盖记录包含 PreCompact、PostCompact、SessionStart 与 context 注入及 resume 重放主题；记录明确为 runtime_verified=false。",
          "level": "official_documentation",
          "source_ids": [
            "resume-official-docs",
            "resume-controls"
          ],
          "limits": [
            "这里引用固定的研究记录，不声明官网有对应版本快照，也不能证明当前 build 或配置实际执行了这些路径。"
          ]
        },
        {
          "id": "claim-resume-preservation-criteria",
          "statement": "项目的 handoff 要求跨生命周期核对纠正、近期原话、来源身份与恢复状态。",
          "level": "authored_source",
          "source_ids": [
            "resume-continuity"
          ],
          "limits": [
            "这些是 candidate 的保留要求，不能证明一次 resume 已满足它们。"
          ]
        },
        {
          "id": "claim-resume-fixture",
          "statement": "合成 fixed 阶段包含明确标记的 continuation prompt；partial 阶段仅包含已声明观察的 model/system/tools。",
          "level": "synthetic_fixture",
          "source_ids": [
            "resume-fixture"
          ],
          "limits": [
            "字面的 resume 提示不能证明执行过 resume 或成功 reload。"
          ]
        },
        {
          "id": "claim-resume-actual-unassessed",
          "statement": "真实 resume/continue 的输入装配、重载来源、轮次关系和模型行为仍未评估。",
          "level": "unassessed",
          "source_ids": [
            "resume-map"
          ],
          "limits": [
            "本轮没有执行 native resume、compact 或 provider 请求。"
          ]
        }
      ]
    },
    {
      "id": "partial-absence",
      "title": "未观察字段保持未知",
      "explanation": "只观察 system/tools 的 capture 无法判断 messages 是否已退出；不能把未观察当成已删除。",
      "claims": [
        {
          "id": "claim-partial-unobserved-different",
          "statement": "对于 partial request body，未观察到某个顶层字段，不构成该字段已缺失的证据。",
          "level": "authored_source",
          "source_ids": [
            "partial-contract",
            "partial-code",
            "partial-cases"
          ],
          "limits": [
            "合同只覆盖明确提供给本地工具的材料，不能证明 provider 或服务端历史。"
          ]
        },
        {
          "id": "claim-partial-fixture",
          "statement": "合成 partial 阶段声明 model/system/tools，并同时从 body 和 observed-field 清单中省略 messages。",
          "level": "synthetic_fixture",
          "source_ids": [
            "partial-fixture"
          ],
          "limits": [
            "这是声明的部分观察形状，不能推成真实请求没有 messages。"
          ]
        },
        {
          "id": "claim-partial-absence-unassessed",
          "statement": "这份 partial capture 无法判断 messages、服务端注入的 context 或模型后续可见内容是否缺失。",
          "level": "unassessed",
          "source_ids": [
            "partial-code"
          ],
          "limits": [
            "实现保留 unknown scope，不从未观察推断 absence。"
          ]
        }
      ]
    }
  ],
  "sources": [
    {
      "id": "compact-doc",
      "title": "Compact 控制的证据分层",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/compact-control.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "四层证据必须分开"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/compact-control.md",
      "limits": [
        "该页明确记录 compact runtime 层尚未观察。"
      ]
    },
    {
      "id": "compact-types",
      "title": "历史 2.1.289 compact 字段记录",
      "kind": "target_runtime_artifact",
      "revision": "@anthropic-ai/claude-code-darwin-arm64@2.1.289",
      "observed_on": "2026-10-05",
      "path": "references/target-runtime-2.1.289.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/findings"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/target-runtime-2.1.289.json",
      "limits": [
        "该 locator 指向保留报告中的字段与 union 记录，不是完整 declaration diff。",
        "历史 target types 不能证明事件执行。"
      ]
    },
    {
      "id": "compact-fixture",
      "title": "合成有损摘要 fixture",
      "kind": "synthetic_fixture",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "experiments/recipes/cases/compact-resume.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/steps/1/capture/body/messages"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/compact-resume.json",
      "limits": [
        "摘要和省略都由作者构造为合成输入。"
      ]
    },
    {
      "id": "compact-types-doc",
      "title": "历史目标 build 的项目报告",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-10-05",
      "path": "docs/target-runtime.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "目标类型带来的修订"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/target-runtime.md",
      "limits": [
        "该页记录保留 artifact 的研究结果，不是新一轮平台观察。"
      ]
    },
    {
      "id": "resume-controls",
      "title": "官方控制面的历史研究记录",
      "kind": "official_documentation_report",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-10-05",
      "path": "docs/official-controls.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "官方控制面核对"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/official-controls.md",
      "limits": [
        "仅阅读选定官方段落，没有保存官网全站快照。",
        "Git revision 固定本项目的报告，不是官网文档版本。"
      ]
    },
    {
      "id": "resume-official-docs",
      "title": "Hooks 文档的历史覆盖记录",
      "kind": "official_documentation_report",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-10-05",
      "path": "references/official-docs.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/sources/10"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/references/official-docs.json",
      "limits": [
        "该记录包含选定 hook、compact/reload 与 resume 重放主题，runtime_verified=false。",
        "Git pin 固定覆盖记录；官网原 URL 不作为不可变版本，本轮没有重新抓取该页面。"
      ]
    },
    {
      "id": "resume-continuity",
      "title": "连续性 handoff 要求",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/continuity-and-memory.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "Handoff 要保住的内容"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/continuity-and-memory.md",
      "limits": [
        "这是 candidate 保留判据，不是已部署的 reload 实现。"
      ]
    },
    {
      "id": "resume-fixture",
      "title": "合成 compact/resume fixture",
      "kind": "synthetic_fixture",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "experiments/recipes/cases/compact-resume.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/steps/2/capture/body/messages/3"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/compact-resume.json",
      "limits": [
        "continuation 提示是合成文本。"
      ]
    },
    {
      "id": "resume-map",
      "title": "Context 地图的生命周期边界",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/context-map.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "改写时保留什么"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-map.md",
      "limits": [
        "该地图要求独立生命周期证据，本身不能替代该证据。"
      ]
    },
    {
      "id": "partial-contract",
      "title": "请求观察的 partial scope 合同",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/request-observation.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "部分 request body：只声明观察到的顶层字段"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/request-observation.md",
      "limits": [
        "合同描述导入材料，不认证 native provenance。"
      ]
    },
    {
      "id": "partial-code",
      "title": "Partial evidence-scope 实现",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "context_lab/observations.py",
      "locator": {
        "kind": "python_symbol",
        "symbol": "_evidence_scope"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/context_lab/observations.py",
      "limits": [
        "源码存在和本地测试不认证 native capture format。"
      ]
    },
    {
      "id": "partial-cases",
      "title": "Case pointer 与 partial-scope 行为",
      "kind": "authored_source",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "docs/context-cases.md",
      "locator": {
        "kind": "markdown_heading",
        "heading": "输入合同"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/docs/context-cases.md",
      "limits": [
        "规则仅适用于显式提供 case 的 body 位置。"
      ]
    },
    {
      "id": "partial-fixture",
      "title": "合成 partial system/tools capture",
      "kind": "synthetic_fixture",
      "revision": "34bc41ae80c0f5f2047b1cc272dd1663d4569a9c",
      "observed_on": "2026-11-13",
      "path": "experiments/recipes/cases/compact-resume.json",
      "locator": {
        "kind": "json_pointer",
        "pointer": "/steps/3/capture/evidence_scope"
      },
      "url": "https://github.com/IndelibleVivi/cc-context-lab/blob/34bc41ae80c0f5f2047b1cc272dd1663d4569a9c/experiments/recipes/cases/compact-resume.json",
      "limits": [
        "manifest 声明是合成材料，不能认证 capture。"
      ]
    }
  ],
  "caveats": [
    "本投影只绑定已记录的公开 source、合成 fixture 与历史观察；不证明当前平台或指定 CC build 仍具有相同行为。",
    "source inspection、target-types/composition 与真实 request、lifecycle、provider 呈现和模型行为是不同证据层。",
    "三条 recipe 的 native_status 保持 NOT_ASSESSED；本投影不读取请求、不跟随 URL/路径引用、不执行模型或安装。",
    "证据级别逐 claim 原样保留；不存在 readiness、兼容性或整体通过聚合。",
    "离线校验检查当前 checkout 的 locator，以及声明 pin 的格式和 URL 一致性；不联网重取历史文件，不认证任意 claim 的语义。artifact revision 与所引用研究记录的 Git pin 分开阅读。"
  ]
}
```

以上 JSON 是同一 projection 的 canonical 序列化。验证只读取固定 repo-relative 文件与声明 locator，不跟随 URL、material reference、request 路径或 runtime 状态。

</details>
