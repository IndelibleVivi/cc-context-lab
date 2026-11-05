# Owned core 与工具保留

状态：固定合成离线路径；native acquisition、真实 request/lifecycle、模型行为与交付均未由此验证，native 层为 **NOT_ASSESSED**。

## 问题与机制

主指导完整保留，并不自动意味着工具说明也保留。这个例子把 `/system` 中的 owned core、工具 name、完整 `input_schema` 与 description 拆开检查：stripped 阶段只移除使用说明，fixed 阶段恢复它。由此可定位损失发生在哪个输入面，不必先重写整套 profile。

机制相关阅读：[Context 来源地图](../context-map.md)、[Profile 设计](../profile-design.md)、[官方控制面](../official-controls.md)、[Mods 迁移](../mods-migration.md) 与 [目标 runtime](../target-runtime.md)。这些链接帮助理解输入面与边界，不是本 recipe 的逐 claim 版本绑定。

## 重跑与阅读

```sh
python3 scripts/run_context_case.py experiments/recipes/cases/owned-core.json --out .cache/recipe-owned-core
python3 scripts/build_context_atlas.py --recipe owned-core --out .cache/cc-context-workbench
```

runner 预期退出 **1** 并写出报告，因为它保留了有意的结构反例。退出 2 是错误，不能算预期结果。打开 `.cache/recipe-owned-core/report.json` 或生成的 Workbench 页面，按阶段查看原值与比较。

先看 baseline → stripped，再看 stripped → fixed。完整 core 和 schema 应逐值相等，工具名也应保留；`missing_guidance_counterexample` 则必须 FAIL，`guidance_restored` 必须 PASS。schema 的声明存在不能证明工具可调用，null description 也不能直接证明工具执行失败。

| Check ID | 预期 |
| --- | --- |
| `core_retained_after_strip` | `PASS` |
| `core_retained_after_fix` | `PASS` |
| `schema_retained_while_guidance_missing` | `PASS` |
| `schema_retained_after_fix` | `PASS` |
| `tool_name_retained_after_strip` | `PASS` |
| `tool_name_retained_after_fix` | `PASS` |
| `missing_guidance_counterexample` | `FAIL` |
| `guidance_restored` | `PASS` |

| Requirement ID | 预期 |
| --- | --- |
| `req_core_present` | `PASS` |
| `req_tool_schema` | `PASS` |
| `req_tool_guidance` | `FAIL` |
| `req_behavior` | `NOT_ASSESSED` |

requirement 汇总包含所有关联阶段：反例保留下来的 FAIL 不会因 fixed 阶段通过而消失。意外的“全绿”可能说明反例被削弱；先核材料与检查，不把它当作改善。

## 诊断、代价与恢复

如果 core 检查失败，检查 `/system` 的完整正文；如果 schema/name 失败，检查具体工具对象；如果只有 guidance 失败，恢复该工具的自有说明。将改动限定在 description 可以减少误改 schema 与执行约定的成本，但仍须单独核对 provider、权限和工具结果交付。恢复后先检查 request，再决定是否进行获授权的模型/工具行为验证。

下一步如需进入实际 CC 材料，按 [显式 CC run 导入](../cc-runs.md) 保存选择与证据缺口，再读 [native 采集协议](index.md#native-acquisition-protocol)。协议当前 **NOT_EXECUTED**，不由离线结果产生新的执行权限。返回 [手册入口与症状导航](index.md)。
