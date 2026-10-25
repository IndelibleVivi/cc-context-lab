# 接入受管 runtime 的准备路径

本仓库负责形成可复用研究、候选规则与实验结果。已有 runtime repo 继续负责部署入口、启动参数、hooks、MCP、candidate 和 rollback。当前阶段只做本地研究，不连接或修改 VPS。

## 谁拥有什么

| Surface | Authority |
| --- | --- |
| 本 repo 的 context map / profile design | 研究范围和候选行为 |
| 上游 revision 与官方 build 类型 | 相应版本的接口/实现证据 |
| 原 runtime repo 的 source 与 renderer | 如何装配实际 candidate |
| 原 runtime 的 selector / controller | 选中哪份 candidate、如何启动和恢复 |
| 真实 request 与 owner 使用结果 | 实际输入和行为；不能由 source 推定 |

## 下次要改之前的定位顺序

1. 从目标 runtime repo 的 current-state 选择 source line，核对 working tree；普通目录、最新 mtime 和历史 green tests 不代表正确基线。
2. 找出主提示与 CLAUDE.md 的装配处、启动参数 allowlist、hook registration、MCP template、动态 context composer 和恢复路径。
3. 明确规则要改的是默认模板、应用事实还是外部原文。来源开关可能同时关闭当前身份、skills 或文件加载，先写清替代路径。
4. 在目标 repo 的 canonical renderer 中准备 source change 和合成验收。不能绕过受管 launcher，用第二个 wrapper 偷塞启动参数，也不能在本 repo 复制一份会漂移的生产 settings。
5. 获得当次生产操作授权后，再按该 repo 的 runbook 确认 VPS 当前版本、selector、inactive candidate、activation 与 rollback。保留新会话、resume、compact 和子代理的独立证据。

这是后续操作的阅读路径，不是本次执行清单。机器专属 source 位置、现有 CC 配置与私人身份正文不进入此 repo；保存在 operator 的 Git 外工作记录。

## 对历史 context 清理的特殊说明

标记式 transcript pruner 和默认 harness 改写是相邻问题。前者可以针对自己的 `hook_additional_context` 清空旧正文并保留记录链条；它不自动移除原厂主提示，也不证明当前进程会重读磁盘。验证时同时观察文件结果和之后实际发出的 request，保留非目标消息与可恢复原件。

当前不执行真实 transcript 改写。离线 fixture 足以验证选择逻辑；进程内历史行为仍需单独实验。

历史教程的有界原函数复现现见 [Context retention](context-retention.md)：settings 中多个 hooks 的排列不能保证顺序；捕获写异常不等于原文件未变。同 inode / advisory lock 与 producer 串联分别解决部分问题，均不能替代活跃进程的下一次 request 验收。本轮没有把研究发现应用到任何生产 pruner。

## Forge / Swap 的 source 定位

已有应用若拥有 canonical ledger 与 lifecycle controller，优先核对它的完整回合选择、handoff artifact、provider adapter、SessionStart mount 和失败恢复。仅找到一个 `rebuild` 文件不足以确认 Forge：quarantine 后重建和主动续窗可能是不同入口。操作的真实语义见 [continuity and memory](continuity-and-memory.md)，不要直接沿用社区同名命令。

本专题已只读核对现有自有实现并运行相关本地合成回归；机器映射、配对 working-tree 状态与详细结果留在 Git 外的既有 continuity。研究库不复制另一 repo 的 controller 或私有配置。下一次接入前仍需核对目标 CLI、writer 的实际工具池、system snapshot、hook 真实交付与普通下一轮行为；本地 receipt 只证明其记录的准备阶段。
