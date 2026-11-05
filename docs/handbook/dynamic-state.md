# 动态 state、版本与纠正

状态：固定合成离线路径；native acquisition、真实 request/lifecycle、模型行为与交付均未由此验证，native 层为 **NOT_ASSESSED**。

## 问题与机制

新的 ambient state 可以作为本轮输入加入，旧值仍作为历史保留。这个例子先注入 revision 2，再保留用户纠正并加入 revision 3；另设 history_dropped 阶段，故意把 revision 1 改写掉。研究的是声明位置与原值，message role 本身不能证明来源或真实注入时机。

机制相关阅读：[Context 保留](../context-retention.md)、[连续性与 Memory](../continuity-and-memory.md)、[请求观察](../request-observation.md) 与 [伴侣 context](../companion-context.md)。这些链接帮助理解输入面与边界，不是本 recipe 的逐 claim 版本绑定。

## 重跑与阅读

```sh
python3 scripts/run_context_case.py experiments/recipes/cases/dynamic-state.json --out .cache/recipe-dynamic-state
python3 scripts/build_context_atlas.py --recipe dynamic-state --out .cache/cc-context-workbench
```

runner 预期退出 **1** 并写出报告，因为它保留了有意的结构反例。退出 2 是错误，不能算预期结果。打开 `.cache/recipe-dynamic-state/report.json` 或生成的 Workbench 页面，按阶段查看原值与比较。

按 baseline、stale、history_dropped、fixed 阅读。fixed 应保留 revision 1 与 revision 2 的历史，并包含精确 correction 和新的 revision 3。`history_dropped_counterexample` 必须 FAIL；其余保留检查应 PASS。较新 revision 出现在新位置，只能证明作者声明的输入形状，不能证明模型将其当作 current。

| Check ID | 预期 |
| --- | --- |
| `revision_2_injected` | `PASS` |
| `revision_3_is_current` | `PASS` |
| `correction_exact` | `PASS` |
| `revision_2_retained_in_fixed_history` | `PASS` |
| `old_state_retained_in_history` | `PASS` |
| `history_dropped_counterexample` | `FAIL` |
| `old_state_retained_after_correction` | `PASS` |

| Requirement ID | 预期 |
| --- | --- |
| `req_current_revision` | `PASS` |
| `req_correction` | `PASS` |
| `req_history` | `FAIL` |
| `req_behavior` | `NOT_ASSESSED` |

requirement 汇总包含所有关联阶段：反例保留下来的 FAIL 不会因 fixed 阶段通过而消失。意外的“全绿”可能说明反例被削弱；先核材料与检查，不把它当作改善。

## 诊断、代价与恢复

历史看起来“脏”不意味着应该重写。先识别 state producer、freshness 语义、新注入位置与原话纠正，再检查 superseded 值是否保留为 history。若历史被替换，恢复旧记录并追加最新 snapshot；若纠正丢失，恢复精确文本。保留多版本会增加阅读与输入成本，但可以检验来源与纠正关系；是否压缩应另有保留要求和证据。真实 hook 顺序、compact/resume 后重建和模型选择仍需 target-native 观察。

下一步如需进入实际 CC 材料，按 [显式 CC run 导入](../cc-runs.md) 保存选择与证据缺口，再读 [native 采集协议](index.md#native-acquisition-protocol)。协议当前 **NOT_EXECUTED**，不由离线结果产生新的执行权限。返回 [手册入口与症状导航](index.md)。
