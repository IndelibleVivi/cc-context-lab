# 持续维护

更新方式：本地按需更新。当前没有 scheduler 或自动后台任务。每次 CC 升级、上游机制变化，或准备修改目标 runtime 配置时，从此页重新进入。

从 repo root 运行下面的只读命令即可比较七个公开上游的 branch tip 与已读 revision。需要 Python 3.10+、Git 和 GitHub 网络访问，无新增 Python 依赖：

```sh
python3 scripts/check_upstreams.py
```

脚本只通过 `git ls-remote` 查询公开 refs，不更新 catalog、clone、安装或启动 Claude。退出码 `0` 表示全部未变，`1` 表示有新 revision 待阅读，`2` 表示至少一项未能查询；网络失败不会被当成“没有更新”。tip 未变也不代表目标 CC runtime 已兼容。

## 一轮更新

1. 读 [current-state](current-state.md)，确认本轮需要解决的差异。
2. 查看 [upstream catalog](../references/upstreams.json) 的已读 revision，读取对应上游当前 revision；先看相关路径的变化，不自动更新安装。
3. 按 [official source list](../references/official-docs.json) 复核涉及的官方参数、事件和版本；有目标安装时对照其生成的 types，公开文档不能覆盖具体 build 的相反证据。
4. 更新同一份 [upstreams](upstreams.md)、[official controls](official-controls.md) 或对应主题，写清新结论是 source reading、作者声明还是实际实验。
5. 有行为规则变化时运行相关合成 fixture；真实模型和生产操作只在对应授权范围内进行。
6. 将当前结论修订回 current-state，保留有意义的历史 revision；私人机器定位与 handoff 在 Git 外更新。

上游代码可以缓存到被忽略的 `.cache/`，不要在本 repo 下执行它的 installer、patcher 或真实模型 tracer。研究笔记引用 exact commit 下的相关文件，避免未来 `main` 改变让旧结论失去上下文。

## 证据写法

- **文档确认**：明确参数或事件合同，附查阅日期和官方 URL。
- **源码确认**：附 repo revision 与 inspected path，只声称源码能够证明的行为。
- **离线验证**：写明合成输入与实际输出；不能外推兼容或模型行为。
- **真实 request / 行为验证**：写明目标版本、场景与结果；原始私人材料不入 Git。
- **未验证 / 待重新取回**：说明缺什么，保留下一条有用阅读路径。

不用一个笼统的“verified”覆盖全部层级。不按日期无限追加一套 current-state；同一结论变更回到它的权威页面。

## 发布边界

远端目前为 private，尚未选择公开 license。要公开发布时另行确定读者、材料范围和权利；private visibility 也不授权上传私人 reference log、外部 continuity、cache 或第三方全文。提交使用 explicit paths，并检查拟提交内容；真实实验和 VPS 操作继续按各自授权范围执行。
