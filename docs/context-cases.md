# Context case：把问题带过输入、历史与换窗

一个 case 固定同一个问题、保留要求、可选的合成 study plan、多阶段 capture 和显式检查。它帮助研究者回答“哪些明确条件满足了、哪里失败、还缺什么材料”。阶段顺序和关联由研究者声明，不是工具独立观察到的运行链；结构检查不判断模型理解、相处质量或外部交付。

## 完整使用路径

先用不含私人数据的示例跑通：

```sh
python3 scripts/run_context_case.py --demo --out .cache/context-case
python3 scripts/build_context_atlas.py --case .cache/context-case/case.json
```

示例有意保留 FAIL 和 NOT_ASSESSED，首条命令会返回 **1** 并生成完整报告。这是可检查的反例，不是命令损坏；如果写成 shell pipeline，不要因预期的 1 丢掉报告。默认 Atlas 也提供同一案例的源码生成示例。所有 captures 是手工构造的合成输入；关联的 study 仍由 canonical companion 引擎执行，不能把两者的关联说成真实 tracing 或引擎生成的请求。

打开“研究案例”可以查看每项要求、声明的阶段、完整 request body 和检查原值，按 PASS / FAIL / NOT_ASSESSED 筛选；显式比较可跳到“请求观察”。关联的 study 可恢复到“对照研究”，会替换当前未保存的 study 编辑，应先下载需要保留的 plan；case snapshot 不变。如果 study snapshot 含超出浏览器安全整数范围的值，恢复入口禁用，也不会自动恢复或进入普通 study 的可编辑情境列表；该视图会提示当前使用独立情境。使用 canonical case 在 CLI 重跑。

下载 case JSON 保存完整输入；report JSON / Markdown 保存本次计算结果。将完整案例带入 brief 后，附件固定在带入时的状态，继续选择其它阶段、请求或 study 不会改变它。重新计算需要运行 CLI，并用 `--case` 重新生成页面；浏览器没有另一套检查器，也没有自动保存。case 固定输入 snapshot，不包含引擎源码；重跑使用当前代码，跨代码版本不保证结果相同。

## 输入合同

`harness-context-case/1` 是 self-contained JSON，准确包含以下字段：

| 字段 | 意义 |
| --- | --- |
| `case_id`、`title`、`question` | 稳定案例标识、标题和研究问题；非空字符串 |
| `requirements` | `{id,text,level}` 数组；level 为 `request_structure`、`model_behavior` 或 `external_delivery` |
| `study_plan` | 完整的 `cc-context-study/1` snapshot 或 null；由既有 study runner 校验和执行 |
| `steps` | `{id,label,capture}` 数组；capture 是完整或显式 partial 的 [capture envelope](request-observation.md) 或 null |
| `comparisons` | `{id,baseline,candidate}` 数组；两侧是显式 step ID，不按位置、名称或相似正文自动配对 |
| `checks` | 下述结构检查数组；引用 requirement 与 step ID |

同类 ID 不得重复，非空 capture 的 capture_id 也不重复；错绑引用、未知字段或 operator 拒绝执行。case 不加载另一个文件、URL、body_ref 或服务端历史。需要增加真实 capture 时，由操作者明确将已取得的材料放入 snapshot，保持原 evidence 和 runtime 条件，不把调用者声明升级成独立证明。

检查字段准确为：

```json
{
  "id": "core_retained",
  "requirement_id": "owned_core",
  "step_id": "after_change",
  "pointer": "/system/0/text",
  "operator": "equals",
  "expected": "SYNTHETIC_CORE"
}
```

pointer 针对**原始 request body**，使用 [RFC 6901 string form](https://www.rfc-editor.org/rfc/rfc6901)：空字符串是根，`~1` 表示 `/`，`~0` 表示 `~`。不接受 URI fragment，也不展开 wildcard；key 中的 `#`、`*` 是字面字符。没有隐式 Unicode/空白归一化；contains_text 的非空期望可由空白组成。

| operator | expected | 检查范围 |
| --- | --- | --- |
| `exists` | null | 此位置可解析到一个显式 JSON 值；值为 null 仍存在 |
| `absent` | null | 明确缺少最后一个 object key 或 canonical array index 越界；不证明内容已全局删除 |
| `equals` | 任意有限 JSON | 原值相等；bool 与 number 区分，对象键顺序不影响比较，字符串/数组顺序保留 |
| `contains_text` | 非空字符串 | 只在此位置是字符串时检查原样子串，不递归扫描或 stringify 整个 subtree |

缺少 capture、祖先节点不存在、类型阻断和非法数组索引都记 NOT_ASSESSED，不能给
`absent` 一个假阳性。若 pointer 的顶层字段不在 capture 的
`evidence_scope.observed_fields` 中（partial body），任何 operator 也记
NOT_ASSESSED，包括 `absent` 和 `exists`：**未观察不等于不存在**。字段在观察范围内、
但 body 没有该成员时仍是明确缺失；`messages: []` 是观察到的空数组，也不能与
unobserved messages 混同。`null`、`false`、空数组与不存在分别保留。含未展开服务端
引用时，检查始终只覆盖显式 body；不能据此声称隐藏历史也被删除。

对 partial capture，空 pointer（body 根）同样始终记 NOT_ASSESSED，并标
`scope_reason=partial_body_root`；该结论适用于 `exists`、`absent`、`equals` 等所有
operator。case check 描述 request body 内容，partial shape 不能证明整个提交文件或完整
请求存在。完整 v1 capture 的 body-root 检查保持原语义。

省略 `evidence_scope` 的既有完整 capture 继续使用完整 body 检查语义。partial
snapshot 不补 `messages: []`，case JSON、report JSON/Markdown、Atlas 与 fixed brief
保留 `request_body: partial`、观察字段和未评估原因。这些 shape 证据不证明
server/provider 注入、模型收到、真实 provenance 或 lifecycle，也不把结构性
PASS/FAIL 升级为模型行为或交付结论。

只有 request_structure 要求可以关联这些检查：任一失败则该要求 FAIL，未失败但有未评估项则 NOT_ASSESSED，其余全部通过才 PASS；没有检查的要求仍未评估。模型行为与外部交付始终 NOT_ASSESSED，不因请求里出现某段文字或所有结构检查通过而升格。要求和检查本身由研究者声明，工具不证明验收条件设计正确，也不输出全案例 readiness 分数。

## 输出、退出码与保护

输出为 `case.json`、`report.json`、`report.md`，分别保留输入快照、同次 canonical
计算和可读报告。报告包含实际 body、evidence scope、期望/原值、未评估项、阶段条件和
完整或部分范围内的比较；报告中的 partial 比较分别列出 comparable 与 unobserved 顶层字段，
不会把未观察位置写成 added/removed。JSON 数值沿用 Python parser 的边界，原始 JSON
排版与数值词法形式不保留。浏览器显示与下载使用 Python canonical 字符串，避免大整数舍入。

CLI 返回 0 表示成功生成且没有结构要求 FAIL，返回 1 表示成功生成且发现结构 FAIL，返回 2 表示输入、校验或输出错误。0 不代表所有要求通过或允许接入生产；NOT_ASSESSED 必须另外阅读。

输出仅限 Git 外或 repo 的 ignored 目录；`--case` 同样适用 Atlas 的私人输出限制，不能与独立 `--study` / `--capture` 混用。输入 case 与输出 case.json 同一路径时保留原输入字节，输入与其它输出 alias 则拒绝。写入前完成校验、render、编码与 alias/软链检查，复用 [共享 writer](../context_lab/artifacts.py) 逐文件替换；不是多文件事务。坏输入不能以空案例或默认示例静默替代。

实际 capture、原始正文、身份与生成的私人报告即使在 private remote 也不提交。source / 合成回放 / 导入者声明 / 真实 provenance / 模型行为仍分别验收；本工具没有采集器、transport、安装器或 scheduler。
