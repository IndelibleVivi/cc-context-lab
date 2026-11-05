# Compact、resume 与部分证据

状态：固定合成离线路径；native acquisition、真实 request/lifecycle、模型行为与交付均未由此验证，native 层为 **NOT_ASSESSED**。

## 问题与机制

compact 的新投影可能保留旧规则，却漏掉稍后的纠正。resume prompt 的出现也不会自动修复 summary。这个例子分别保留旧指导、精确 correction、summary 与续接输入，并增加只观察 model/system/tools 的 partial capture，检验未知 messages 不会被误判为删除。

机制相关阅读：[Compact 控制](../compact-control.md)、[连续性与 Memory](../continuity-and-memory.md)、[请求观察](../request-observation.md) 与 [Context case](../context-cases.md)。这些链接帮助理解输入面与边界，不是本 recipe 的逐 claim 版本绑定。

## 重跑与阅读

```sh
python3 scripts/run_context_case.py experiments/recipes/cases/compact-resume.json --out .cache/recipe-compact-resume
python3 scripts/build_context_atlas.py --recipe compact-resume --out .cache/cc-context-workbench
```

runner 预期退出 **1** 并写出报告，因为它保留了有意的结构反例。退出 2 是错误，不能算预期结果。打开 `.cache/recipe-compact-resume/report.json` 或生成的 Workbench 页面，按阶段查看原值与比较。

先看 pre-compact baseline，再比较 compacted_stale → compacted_fixed，最后看 fixed → partial。`summary_correction_counterexample` 必须 FAIL；fixed 的原指导、纠正、summary 与 resume 检查应 PASS。`partial_messages_absence_unproven` 必须是 NOT_ASSESSED：messages 未观察，不是空历史。

| Check ID | 预期 |
| --- | --- |
| `old_guidance_retained` | `PASS` |
| `correction_exact` | `PASS` |
| `summary_correction_counterexample` | `FAIL` |
| `summary_retains_correction` | `PASS` |
| `resume_prompt_present` | `PASS` |
| `partial_messages_absence_unproven` | `NOT_ASSESSED` |

| Requirement ID | 预期 |
| --- | --- |
| `req_old_guidance` | `PASS` |
| `req_correction` | `FAIL` |
| `req_resume` | `PASS` |
| `req_partial_scope` | `NOT_ASSESSED` |
| `req_behavior` | `NOT_ASSESSED` |

requirement 汇总包含所有关联阶段：反例保留下来的 FAIL 不会因 fixed 阶段通过而消失。意外的“全绿”可能说明反例被削弱；先核材料与检查，不把它当作改善。

## 诊断、代价与恢复

summary 丢纠正时，分别检查保留历史与 compact 投影，不要仅追加一句 resume 就宣布恢复。恢复纠正并让新窗口可读取，再明确是否重注入 current state。保留原话与 summary 两份内容有输入成本，但能分开检查原话损失和压缩损失。真实接入时记录 manual/automatic/plugin/precompute 路径、compact 输入输出及下一份 request；随后单独观察模型使用与用户交付。合成 resume 字符串不是执行过 `/compact` 或 resume 的证据。

下一步如需进入实际 CC 材料，按 [显式 CC run 导入](../cc-runs.md) 保存选择与证据缺口，再读 [native 采集协议](index.md#native-acquisition-protocol)。协议当前 **NOT_EXECUTED**，不由离线结果产生新的执行权限。返回 [手册入口与症状导航](index.md)。
