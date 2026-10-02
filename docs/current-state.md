# 当前研究状态

更新：2026-10-03（Asia/Singapore）。状态：private 研究 repo，实验仍在本地；工作名 `cc-context-lab` 已选用，正式名称未定。

## 当前判断

1. 把默认 harness 指导整体换成自有 context 的目标，必须覆盖 system、tools、messages 和会话生命周期。只替换主提示不能代表完成。
2. 官方主提示替换、来源开关和 Mods 是不同控制面。优先评估支持的结构化入口；二进制 patch 作为有具体覆盖缺口时的候选，不能预先一概采用或淘汰。
3. `session.compact` 事件存在，不等于所有摘要 prompt 均可替换。resume 的 system snapshot、历史 reminders、普通与 fork subagent 分开验证。
4. 运行事实可以重新表达；来源正文必须保真。engine 生成的消息仍可能包含外部原文。
5. 新 repo 维护研究和实验；已有 runtime 的配置变更回到它自己的 renderer / runbook。本阶段只在本地工作，不动 VPS。
6. 此次读到的 tweakcc upstream 已在 native 路径调用 `applySystemPrompts`；fixed 关于 upstream 跳过 native 的宽泛比较不能继续引用。fixed 的默认摘要行为补丁也必须从 prompt 变化中分离，具体证据见 [upstreams](upstreams.md)。

## 已建立的依据

- 已核对官方 CLI、environment variables、Agent SDK prompt guide、Mods reference/testing/troubleshooting、bare mode 与相关 changelog；入口和查阅范围见 [official controls](official-controls.md)。Mods HTML 页面在一次 web 读取中不可用，随后成功读取同站官方 `.md` 正文。
- 上游源码的 exact revisions、文件覆盖和限制集中在 [upstreams](upstreams.md) 与 [catalog](../references/upstreams.json)，不把可变 `main` 链接当作固定证据。
- 已完成本地受管 runtime 的有界 source 阅读，确认现有 hook 注入、marked transcript pruning、candidate renderer 和启动参数合同。私人机器映射保存在 Git 外，本页不把本机 source 当作 VPS 当前状态。
- 已整理三组完整配置对照、生命周期测试矩阵与结果记录格式；见 [experiments](../experiments/README.md)。
- 本地 `check_upstreams.py` 已实际查询七个公开仓库，全部与本次 pin 一致；合成验证覆盖未变 / 有更新 / 查询失败，对应退出码 0 / 1 / 2。此检查不读取或改变 CC 安装。
- 已对 roof-mod 原 handler 完成 F02/F03/F04 三项合成缺陷复现：引用 preamble、非 engine 同类型事件和 channel guard 范围；不是官方 plugin test 或真实 CC 验收，见 [实验记录](../experiments/README.md)。

## 仍未验证

- 本机或 VPS 安装版本、实际 Mods 开关和加载状态；当前目标 build 生成的完整类型声明。
- 新会话 / compact / resume / subagent 的真实 request bodies，以及实验三组的行为差异。
- 各 patch 工具对目标安装方式与版本的兼容性、非提示副作用、升级和恢复结果。
- 修改落盘 transcript 对正在运行进程的真实输入影响。
- 独立归档教程与云盘备份正文：尚未在本专题重新取回；本次讨论 reference 不是那些原始资料的替代品。

以上是后续研究问题；不妨碍本研究库已可使用，也不构成运行时方案已完成的声明。

## 下一步

先把 `lobotomized` 的 override 意图与 `tweakcc-fixed` 的实际应用路径对应起来，再逐类判断哪些能迁到 Mods、哪些仍无对应入口。优先完成有来源边界的离线 fixture；只有需要真实请求证据时再单独安排隔离模型实验。保留完整目标，单个 fixture 的完成不能替代整个 context 生命周期验收。

GitHub 远端已建立为 [IndelibleVivi/cc-context-lab](https://github.com/IndelibleVivi/cc-context-lab)，visibility 已核为 private，研究内容由 `main` 管理。没有公开发布、安装插件或部署；远端 refs 不代表任何 CC runtime 已更新。私人材料与上游缓存不进入远端。
