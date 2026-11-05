# CC 本地 request 观察与结构比较

更新：2026-11-01。此页拥有通用观察入口、证据与私人数据边界。`context_lab/observations.py` 拥有结构投影合同；Claude Code 的 Mods、来源开关和实际生命周期仍归各自专题。支持一种 wire format 不代表已经验证使用该格式的所有 harness。

## 可以完成的操作

把明确提供的本地 request body 包在 capture envelope 中，记录 harness/build、入口、模式、candidate 和 session 路径，然后检查 instructions、messages/input、tools 与其余参数。比较两份材料时，运行条件和原值变化一起保留。

```sh
# 完整合成示例，无网络、CC binary 或模型
python3 scripts/inspect_context.py experiments/request-observation/fixtures/anthropic-a.json \
  --compare experiments/request-observation/fixtures/anthropic-b.json \
  --out .cache/request-observation

# 另一种 wire format
python3 scripts/inspect_context.py experiments/request-observation/fixtures/responses-a.json \
  --compare experiments/request-observation/fixtures/responses-b.json \
  --out .cache/request-observation-responses
```

单个 capture 输出 `observation.json`、`report.md`；带 `--compare` 输出 `comparison.json`、`report.md`。退出 0 表示本次本地读取/投影/写出成功；非法输入或 I/O 失败退出 2。它不查询账户、凭据、服务端会话、安装状态或模型。

## Capture 是输入材料，不是执行配置

以下结构以合成材料示意：

```json
{
  "schema": "harness-context-capture/1",
  "capture_id": "example-request-a",
  "evidence": {"kind": "synthetic_fixture", "observed_at": null},
  "runtime": {
    "harness": "example-harness",
    "version": "synthetic",
    "entrypoint": "example-entry",
    "mode": "synthetic",
    "candidate": null,
    "session_path": "new-session"
  },
  "wire_format": "anthropic-messages",
  "body": {
    "model": "synthetic-model",
    "max_tokens": 128,
    "system": "Synthetic guidance only.",
    "messages": [{"role": "user", "content": "A synthetic message."}]
  }
}
```

`runtime.harness` 为非空标签，其余未记录的 runtime 字段可以为 null；`session_path` 描述 new/compact/resume/subagent 等被观察的路径，不要求机器上的文件地址。`observed_at` 是调用者记录的 ISO datetime 或 null，不由页面生成日期补足。顶层未知 manifest 字段、重复 JSON keys、nonfinite 数值和错误结构会拒绝；request body 内的未知参数和 item 则保留。

### 部分 request body：只声明观察到的顶层字段

当材料明确只有 system/tools 等部分 shape、没有 messages 时，保留
`harness-context-capture/1`，增加可选 `evidence_scope`。以下合成材料声明
request body 为 **partial**，并列出确实观察到的顶层字段；`body` 中没有
`messages`，工具**不会补成 `messages: []`**：

```json
{
  "schema": "harness-context-capture/1",
  "capture_id": "synthetic-partial-shape",
  "evidence": {"kind": "synthetic_fixture", "observed_at": null},
  "runtime": {"harness": "synthetic-harness"},
  "wire_format": "anthropic-messages",
  "evidence_scope": {
    "request_body": "partial",
    "observed_fields": ["model", "system", "tools"]
  },
  "body": {
    "model": "synthetic-model",
    "system": [{"type": "text", "text": "Synthetic system only."}],
    "tools": [{"name": "synthetic_tool", "input_schema": {"type": "object"}}]
  }
}
```

`evidence_scope` 的 `request_body` 为 `complete` 或 `partial`。省略整个
`evidence_scope` 保持既有 v1 兼容语义：导入的 `body` 是按完整文件对象观察，
Anthropic 的 `messages` 与 Responses 的 `input` 等原有必填结构检查继续生效。
显式 `complete` 只接受 `request_body`，规范化的 observation 还会保留
`observed_fields: null`。

`partial` 必须提供非空且不重复的 `observed_fields`，其每个值都是 body 的
顶层 object key 名称，可包含已观察而明确缺失的成员。**body 中实际出现的每个顶层字段都必须列入**；未列出的字段是
未观察，而不是缺失。不能通过删掉一个已出现字段的声明把它伪装成 unknown。
同一规则适用于未知参数：出现就必须保留并列入；未出现且未声明则仍为 unknown。

以下三种证据不同：

- `messages` 没有作为 body 成员出现，且不在 `observed_fields`：**未观察**。
- `messages` 在 `observed_fields` 中，但 body 没有该成员：在该观察范围内**明确缺失**。
- `messages: []` 同时出现在 body 与 `observed_fields`：这是**观察到的空数组**。

partial 只描述这份导入材料的 shape。它不证明 server/provider 注入、模型收到、
完整模型可见 context、真实 provenance 或 lifecycle。默认完整示例不变；部分
scope 只来自调用者明确的 manifest 声明。

`evidence.kind` 可以是 `synthetic_fixture` 或 `captured_request`。后者仍是**导入者的声明**：输出始终标记 `provenance=imported_manifest`，模型行为与外部交付为 `NOT_ASSESSED`。工具不会独立证明文件确实来自某个 runtime，也不会把合成示例升级为实测。

已有明确的本地 body 时，可用标准库在本机创建 envelope：先准备不含 `body` 的 metadata JSON，再显式读取两个文件；不扫描目录或跟随日志中的路径。

```sh
python3 - metadata.json request.json capture.json <<'PY'
import json, sys
from pathlib import Path
from context_lab.observations import parse_capture_json, normalize_capture
metadata, body, output = map(Path, sys.argv[1:])
capture = parse_capture_json(metadata.read_text())
capture['body'] = parse_capture_json(body.read_text())
normalize_capture(capture)
payload = json.dumps(capture, ensure_ascii=False, indent=2)
payload.encode('utf-8')
with output.open('x', encoding='utf-8') as target:
    target.write(payload)
PY
```

输入和输出均使用你明确选定的私人位置。`open('x')` 拒绝覆盖已有文件。若材料来自 CC，官方 body-file 机制可作为采集候选，但本命令不启用它；已有日志也须先核具体 build、采集模式、截断/脱敏和调用来源。不能凭本地文件存在推定捕获完整。

## 投影与比较的精确边界

| 格式 | 观察位置 | 保留与限制 |
| --- | --- | --- |
| Anthropic Messages | `/system`、`/messages/i`、`/tools/i` | system blocks、midstream system role、tool result、图片、cache metadata 与工具 schema 保留原值 |
| OpenAI Responses | `/instructions`、`/input` 或 `/input/i`、`/tools/i` | 字符串/数组输入、function call/output、reasoning 与未知 item 保留；未识别 item 标 opaque |
| 两者共同 | 完整 request body、其余 request parameters | 未知字段不丢弃，不跟随 URL、body_ref、template 或服务端 state |

section 的 `id` 与 `pointer` 表示请求内位置，不是来源身份。`origin`、`lifecycle` 固定为 unknown：`role:user` 可能装着 tool result、hook wrapper 或外部引用，不能直接当成人类原话；数组尾部也不能自动解释为 current。

同格式按 JSON pointer 对照，保留 added/removed/modified/unchanged；任一侧未观察
对应顶层字段时，row 标为 `unobserved`，不能解释为 added/removed。报告分别列出
`comparable_top_level_fields` 与 `unobserved_top_level_fields`，并给出
`evidence_scope_alignment`。partial 一侧的 `request_body_equal` 只比较双方都观察到的
顶层字段；报告同时用 `request_body_equal_scope` 标明这不是完整 body 相等。
字段全集来自双方 `observed_fields` 的并集，不只看 body 中实际出现的 key，因此“双方都在
观察范围内但都没有该成员”可以表示相同；值比较前先比较成员是否存在，
已知缺失与显式 `null`、空数组或 `false` 不同。
位置变化可能表现为多条差异，不宣称语义归因。跨格式标为
`cross_format_unaligned`，两侧分列，不把相似正文当成等价来源。跨格式中只要某 row 的
对应顶层字段未被另一侧声明观察，该 row 也标为 `unobserved`，不声称删除或新增；
full/full 跨格式保留原有两侧分列语义。对象 key 顺序不计为变化，
字符串空白、数组顺序、省略与显式空值、bool 与 number 分别处理。

JSON 格式空白与数字的原始词法形式不保留，浮点数使用 Python JSON 的原生解析精度；原字符串、结构与整数值保留。Atlas 的原值展示、搜索和 JSON 下载使用 Python 预先序列化的 canonical 字符串，避免大整数经 JavaScript Number 舍入。比较结论由 Python 产生，浏览器不另实现 wire parser 或 diff 引擎。

Responses 的 `previous_response_id`、`conversation` 或 `prompt` 引用会进入 `unresolved_context`。引用未展开，不证明其指向的历史为空；本工具也不从账户或网络取回内容。完整 `request_body` 仍只是导入文件中的完整对象，并非完整模型可见 context 的认证；partial 则连完整文件对象也不声明。

## 在 Atlas 检查与交接

默认 `python3 scripts/build_context_atlas.py` 从问题入口打开 owned-core 合成 recipe 及其阶段 captures；独立 `--capture` 页面仍只包含明确提供的文件，不混入默认案例。打开“请求观察”，先查看单份，或选择已明确准备的 A/B、查看条件变化与原值、检索 section、导出 canonical JSON/Markdown，或固定带入 change brief。

使用明确提供的材料：

```sh
python3 scripts/build_context_atlas.py \
  --capture capture-a.json --capture capture-b.json \
  --out .cache/private-observation-atlas
```

这时仅投影指定 capture，不混入默认示例；重复 capture_id 会拒绝。默认只做单份观察；用 `--pair <baseline-capture-id> <candidate-capture-id>`（可重复）或 `--pairs comparison-pairs.json` 明确准备比较，capture ID 以输入 manifest 为准。缺少 pair 时页面提供选择清单与重建命令，不把缺比较写成没有变化。case 默认只准备自身声明的比较，不做自比较。输出必须在 Git 外或 worktree 的 ignored 目录。页面、`data.json`、下载报告与 brief 都可能包含观察到的私人正文，即使 partial 或 remote private 也不能提交。界面、JSON/Markdown 和 brief 会显示 evidence scope；unobserved 行不冒充缺失或变化。原始 body 标题按 A、B 各自的 scope 显示，partial 一侧标“声明的部分 request body（不是完整请求）”，不影响另一侧保留“完整 body”标签。输出不是自动脱敏产品；synthetic fixtures 以外的材料不进入仓库默认投影。

CC 的显式 request/response/index/event 可先走 [CC run importer](cc-runs.md)，再用 Atlas `--run` 查看；run 的单份/pair导出携带sidecar，完整snapshot可重开。独立capture仍按旧合同读取。

共享 IO policy 在任何 mkdir/staging 前要求 resolved 输出目录及每个目标留在 Git 外或本 worktree 的 ignored且untracked位置；`synthetic_fixture` 也不能绕过。共享 writer 在任何写入前完成 render/UTF-8 编码和路径检查；拒绝 symlink、非普通文件、输入及输出 alias。每个文件先暂存再 atomic replace，已有 hardlink 不会改写另一链接的内容。多个文件不是一个事务，中途文件系统失败可能留下部分已更新的产物，命令返回错误。

## 验证与来源

```sh
python3 scripts/check_offline.py
```

核心 tests 覆盖结构保真、未知字段、证据层、partial system/tools、未观察
messages、观察到空 messages、显式缺失、scope 校验、完整 v1 兼容、跨格式、
declared-absent 与空数组、双方已知缺失相同、partial 字段并集、未知原值、
disjoint-scope 跨格式 non-change、完整/partial 双侧 raw 标题、
输入不覆盖与错误写入；Atlas/Node 回归另保护 canonical JSON、超出 JS 安全范围的
整数、搜索/下载、partial 标签和固定附件。浏览器 QA 仍单独执行，synthetic tests
不代表真实模型或 harness 验收。本轮只用合成输入，没有读取真实 capture 或调用 runtime。

本轮核对 [Anthropic Messages create](https://platform.claude.com/docs/en/api/messages/create)、[OpenAI Responses migration](https://developers.openai.com/api/docs/guides/migrate-to-responses)、[OpenAI conversation state](https://developers.openai.com/api/docs/guides/conversation-state) 和 [CC monitoring](https://code.claude.com/docs/en/monitoring-usage) 的相关输入/引用/采集段落。观察日期与阅读边界见 [source record](../references/request-observation.json)，不是对目标 CC build 或其他 harness 的新运行证明。
