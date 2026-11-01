# 显式导入 CC run，再选择请求比较

更新：2026-11-01。此页拥有 CC 材料导入和 Atlas run 的使用路径。项目仍是跨 harness 的 Context Engineering Lab；CC 是当前优先打通的主线。通用 capture 与 case v1 继续可用。

这条路径读取你明确选定的 request、response、index 和 event 文件，生成可供既有 observer 使用的 captures，并用 `run.json` 保留关联、来源声明、内容损失与缺口。它不启动 CC、不采集日志、不读账号、不跟随 `body_ref` / URL / index 里的路径，也不执行材料中的命令。

## 先跑合成例子

Python 3.10+ 与 Node.js；无需安装依赖或提供 API key。在 repo 根目录执行：

```sh
python3 scripts/import_cc_run.py \
  --selection experiments/cc-runs/fixtures/selection.json \
  --out .cache/cc-run-example

python3 scripts/build_context_atlas.py \
  --run .cache/cc-run-example/run.json \
  --pair synthetic-file-mode:request-main synthetic-file-mode:request-partial \
  --out .cache/cc-run-atlas
```

在浏览器打开 `.cache/cc-run-atlas/index.html`。若需要 loopback 预览，参照 [Atlas 的打开方式](../workbench/README.md#生成与打开)。例子中的三份 request 都应出现：一份有 index 和所选响应，一份未索引，一份只观察到 system/tools。未索引不表示请求失败；未观察 messages 不会补成空历史。

从 **CC Run** 选择请求，先看关联状态和 scope，再点“查看这份 request 原值”。在 **请求观察** 选择 B，查看已准备的比较。没有预先准备的 pair 会显示“未准备此比较”，提供比较选择 JSON 与重建命令；不会显示成“没有变化”。不选 B 即为单份观察，没有自身比较。

`--pair BASELINE CANDIDATE` 可重复；也可用 `--pairs comparison-pairs.json` 读取 `[["capture-a", "capture-b"]]`。拒绝自比较、重复的有向 pair 和未知 ID。默认 case 只准备自己声明的比较；独立 run / captures 默认不准备比较。需要更多 pair 时明确重建，浏览器不另算差异。

## 准备自己的 selection

将要读的文件放在同一私人目录，在旁边创建 `selection.json`。原始输入保持不变，输出另选 ignored 或 Git 外目录。`cc-source-selection/1` 兼容附件种子的 request/response/index 选择；新材料优先使用 `/2`，可额外提供 event、target 与 content losses。

```json
{
  "schema": "cc-source-selection/2",
  "run_id": "example-run",
  "evidence_kind": "captured_request",
  "runtime": {
    "harness": "Claude Code",
    "version": null,
    "entrypoint": null,
    "mode": null,
    "candidate": null,
    "session_path": null
  },
  "target": {"id": "operator-selected-target", "fingerprint": "operator-recorded-fingerprint"},
  "content_losses": [
    {"source_id": "request-01", "kind": "request", "reason": "redacted", "path": "/messages"}
  ],
  "sources": [
    {"id": "request-01", "kind": "request", "path": "request-01.json", "sha256": "REPLACE_WITH_SHA256_OF_SELECTED_FILE_BYTES"}
  ]
}
```

示例 digest 是占位符，必须换成所选文件原始字节的 SHA256，才能导入；该检查用于绑定输入身份。`run_id` 与 source `id` 使用 1–64 个 ASCII 字母、数字、`_`、`-`，首字符为字母或数字；ID 和物理文件不能重复。runtime 的六个字段均显式提供，未知值为 null。`target` 可省略或为 null；fingerprint 是操作员声明的字符串，工具没有据此验证 binary 或有效配置。

source 的 `kind` 为 `request`、`response`、`index`、`event`；可以只导入 response 或 event，不伪造缺失请求。`path` 是相对 selection 的 POSIX 路径，不接受绝对路径、`.` / `..`、空分量或穿过 symlink 的选材。`recorded_path` 可提供与 index 完全一致的别名，它是不会被打开的 metadata。只按精确 alias 关联，不做 basename、后缀或最近时间匹配。

request 可携带 [capture 的 `evidence_scope`](request-observation.md#部分-request-body只声明观察到的顶层字段)。`content_losses` 分别声明选定 source、类型、RFC 6901 pointer 与 `unobserved` / `truncated` / `redacted` / `spilled_reference` / `unknown` 原因；它不改写正文，也不补足缺材料。event 是有独立 identity 的显式 JSON object，保存自己的 id / sequence / source / process / timestamp 与原始 metadata；这是 Lab 的导入合同，不是对任意 OTel exporter 格式的自动适配。不同 process 的 sequence 不拼成全局时序。

本地 importer 使用 macOS/Linux 的 POSIX regular-file 与 no-follow 打开能力；未提供 Windows 原生适配。边界为 manifest 512 KiB、每份原始 source 16 MiB、合计 64 MiB、128 份 source、10,000 条非空 index records。JSON 使用既有 strict parser，重复 keys、nonfinite 数值和坏编码会拒绝。digest 校验先于解释；FIFO 等非普通文件不会让 reader 挂起。没有自动目录发现或对源文件的写入。

## 关联结果怎样读

| 结果 | 可以说明什么 |
| --- | --- |
| `index_association: matched` | 提交的 index 记录了唯一的精确文件关联，不是 provider receipt |
| `unindexed` | 选中了请求，但提交的 index 没有对应记录；响应是否存在保持未知 |
| `ambiguous` / `conflict` | 重复行、重复 request ID、共享响应、alias 歧义或 response ID 矛盾仍在，工具不替你挑一次“成功重试” |
| `selected_response_presence: present` | 至少一份候选响应文件已选中；关联有矛盾时，它仍然存在 |
| `not_selected` | 唯一可解释的引用指向未选择材料；不会据此去读该文件 |
| `unassessed` | 现有材料不足以判断响应存在性；不是已知缺失 |

`attempt_id` 是“一份选定 request artifact”的本地标签，不是原生 retry ID。正文相同也可属于两次请求。timestamp 与阶段标签不会变成已证顺序；没有 agent/process 身份时，列表明确显示未记录，不从 query 名称猜普通主会话或 child。

## 保存、重新打开与交接

导入器输出 `<source-id>.capture.json` 和 `run.json`。保留 sidecar 与 capture 文件；只拿一个旧 capture 去 observer 看结构，会失去 run 层的完整 caveats。

Atlas 从 sidecar 只读取 importer 生成的同目录 capture 文件，核对每份 digest、identity、runtime 与 scope。混合了不同次产物、capture 被改动或名字越界时拒绝。原始 request/response/index 引用继续不展开。Atlas 的单个 run/snapshot 读取和选定文件合计预算为128 MiB；超出时拒绝，不能当作任意规模日志存储。

“下载 run snapshot”生成 `cc-run-snapshot/1`，固定 sidecar 与 capture 的原始序列化文本；可将该文件直接交给 `build_context_atlas.py --run snapshot.json` 重开。Snapshot 不是原始日志归档：保留原 source 文件，文件 hash 不等于把原字节也放入了 snapshot。

从 run 进入请求观察后，JSON 导出为 `cc-run-observation-export/1`：`run` 是 sidecar，`result` 是 canonical observation / comparison。Markdown 和 brief 同样带 run 的损失与限制。这是结果导出；要重开完整 run，用 run snapshot。浏览器只拼接 Python 已编码的片段，不把原值经 JS Number 再序列化。

所有输出目录及每个具体目标都受共享 [IO policy](../context_lab/io_policy.py) 检查：在本仓库内必须 ignored 且未 tracked，或明确在 Git 外。导入者填写 `synthetic_fixture` 也不能绕过。拒绝输入输出 alias、输出 symlink 和非普通目标；render/UTF-8 编码全部结束后才开始写入。逐文件 atomic replace 不构成多文件事务，文件系统中途失败仍需检查整包。

## 当前验证层级与下一步

这里实现的是 source、合成导入、固定 snapshot 和本地浏览路径。没有本轮 native CC 导出、模型调用、真实 resume/compact/child 或行为验收，保持 `NOT_ASSESSED`。结构可读不证明 provider 呈现，也不把声明的 `captured_request` 变成独立 provenance。

格式研究参考 [官方 Monitoring 的 body events](https://code.claude.com/docs/en/monitoring-usage#api-request-body-event)，2026-11-01 复核：file mode 的 index 只覆盖成功响应，因此请求 inventory 必须来自明确选材；正文仍有 thinking redaction 边界。文档合同和本机 native-format acceptance 是两层证据，后者尚未执行。来源记录见 [CC run evidence](../references/cc-runs.json)。

统一检查为 `python3 scripts/check_offline.py`。后续机制/claim 索引、来源 receipt、跨阶段谓词、完整 native recipes 与升级影响报告的当前状态见 [programme](development-programme.md#cc-材料主线2026-11-01)。这些后续工作不由本次导入成功自动获得通过或执行权限。
