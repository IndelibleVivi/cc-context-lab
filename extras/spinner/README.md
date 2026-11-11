# While Claude Works

一个只有 187 个等待词的离线小页面，以及一颗用字符轮廓搭出的六帧星星。它只做展示，不读取 Claude Code 的 session、日志或任务状态，也不代表模型真的在工作。

打开 [index.html](index.html) 即可离线使用；文字、样式和脚本都在这一个文件里，不加载 CDN、字体或依赖。也可以用 [spinner-verbs-2.1.322.txt](spinner-verbs-2.1.322.txt) 直接复制逐行词表。

## 来源与边界

- 词表：Claude Code **2.1.322** 的 187 个内置等待词，来自 2026-11-11 核对过的官方 npm native package snapshot [@anthropic-ai/claude-code-darwin-arm64](https://registry.npmjs.org/@anthropic-ai/claude-code-darwin-arm64/2.1.322)。
- [官方 spinnerVerbs 文档](https://code.claude.com/docs/en/settings-reference#spinnerverbs) 说明等待词的用途；动画规则是本项目独立实现。
- 词表是第三方来源事实，保留原归属；不随本项目的 SUL 或文档许可重新授权。
- 页面代码和独立 CSS/JS 复现属于本项目原创功能实现，按 [SUL-1.0](../../LICENSE) 提供。
- 动画帧为 `· ✢ ✳ ✶ ✻ ✽`，1.2 秒硬切换；静态落点是 `✻`。这是网页复现的设计选择，不声称与 native spinner 的精确时序、实现或行为一致。
- 页面不调用网络，不访问真实模型，也不包含 fake progress 或自动换词。

## 文件

| 文件 | 用途 |
| --- | --- |
| [verbs.json](verbs.json) | 唯一手维护的词表，187 个字符串 |
| [spinner.css](spinner.css) | 可复用的样式；默认作用于 `.cc-spinner-glyph` |
| [spinner.js](spinner.js) | classic browser JS；自动初始化 `[data-cc-spinner]` |
| [template.html](template.html) | 独立页面的模板源 |
| [index.html](index.html) | 生成的单文件离线页面，请勿手改 |
| [spinner-verbs-2.1.322.txt](spinner-verbs-2.1.322.txt) | 生成的逐行词表，请勿手改 |

## 接入

页面需要同时包含词表、样式和脚本。下面为精简的两个词；使用完整187词时，将 `verbs.json` 的原数组内嵌到数据标签中：

```html
<link rel="stylesheet" href="./spinner.css">
<script src="./spinner.js" defer></script>
<script type="application/json" id="cc-spinner-data">["Accomplishing", "Actioning"]</script>

<div data-cc-spinner class="cc-spinner">
  <span class="cc-spinner-glyph" data-spinner-glyph aria-hidden="true"></span>
  <span data-spinner-word aria-live="polite"></span>
  <button class="cc-spinner__button" type="button" data-spinner-next>New word</button>
  <button class="cc-spinner__button" type="button" data-spinner-pause aria-pressed="false" data-label-pause="Pause animation" data-label-resume="Resume animation">Pause animation</button>
  <button class="cc-spinner__button" type="button" data-spinner-download>Download TXT</button>
</div>
```

引入 `spinner.css` 和 `spinner.js` 后，每个 `[data-cc-spinner]` 根节点会独立挂载，按钮与词更新不会碰到其他界面。只有 `[data-spinner-next]` 会明确换词；挂载时也随机取一个词，之后保持不动。暂停按钮只切换根节点的 `data-paused`，不会清理当前词。

- `[data-spinner-glyph]`：符号节点，脚本会补上 `.cc-spinner-glyph`，并设为 `aria-hidden`。
- `[data-spinner-word]`：词的文字节点。
- `[data-spinner-next]`：可选；点击或按 Enter 换词。
- `[data-spinner-pause]`：可选；维护 `aria-pressed` 和根节点状态。可加 `data-label-pause` / `data-label-resume` 提供当前语言的按钮文案。
- `[data-spinner-download]`：可选；将当前传入的词表导出为逐行 TXT；使用完整快照时为187行，不联网。

按钮可以省略；紧凑嵌入只需 glyph 与 word。每页只能有一个 `#cc-spinner-data`。如需程序化挂载，可调用 `CCSpinner.mount(root)`；脚本已经把未挂载的 root 初始化完毕，重复调用不会重复绑定。

`prefers-reduced-motion: reduce` 会自动把动画固定到 `✻`；暂停状态也固定到 `✻`，恢复后继续按 1.2 秒帧序播放。

## 只复用星星

只要装饰动画时，引入 CSS 即可，不需要 JS 或词表。若它承担真实工作状态的提示，请另配可读的状态文字。

```html
<link rel="stylesheet" href="./spinner.css">
<span class="cc-spinner cc-spinner-glyph" aria-hidden="true"></span>
```

## 生成

从仓库根目录运行：

```sh
python3 scripts/build_spinner.py
```

它会读取 `verbs.json`、`spinner.css`、`spinner.js`、`template.html` 与仓库 `LICENSE`，生成 `index.html` 和 TXT。生成页与词表都已纳入版本控制；若改了 canonical source，请重跑 builder 并检查生成物，不要手改生成结果。

`scripts/build_spinner.py` 还提供 `load_spinner_assets(root: Path) -> dict[str, str]`，返回 `css`、`js`、`data_json`，供 Workbench 等离线页面直接内嵌同一份材料。

## 独立下载

`index.html` 不依赖同目录的 CSS、JS 或 JSON，直接作为单文件带走即可。生成 HTML 已内嵌完整 SUL-1.0 正文与来源说明；复制 CSS/JS 时同时携带 [LICENSE](../../LICENSE)。TXT 同样是独立文件；如果从本地仓库使用前端 CSS/JS，保留 `extras/spinner/` 的相对目录布局。

## 验证

```sh
python3 scripts/test_spinner.py
node --test scripts/test_spinner_ui.cjs
node --check extras/spinner/spinner.js
```

测试覆盖数据、生成物、离线内嵌、下载行数、按钮隔离、暂停、reduced-motion 静态落点与缺失控件容错。真实浏览器布局和最终体验仍由集成方做渲染验收。
