# AgentMesh 设计规范（DESIGN.md）

> 视觉单一事实来源。所有原型（`docs/prototypes/`）与前端实现必须遵循本文件。
> 风格：**开发者工具风（GitHub 深色同款）· 单一深色模式 · 紧凑高密度**。
> 若与其他文档冲突，以本文件为准。

## 1. 设计基调

面向开发者/运营的私有化 Agent 平台中台。基调稳重、中性、专业，向 GitHub / Vercel / Linear 这类开发者后台看齐。深色底降低长时间使用的视觉疲劳；等宽字突出 ID / 版本串 / KitOps ref 等机器标识；高信息密度让一屏看到更多资产、实验、遥测行。

原则：信息密度优先、克制用色（主色只用于关键动作与选中态）、状态用语义色不用装饰、无多余阴影与渐变。

## 2. 颜色 Token

```css
:root{
  /* 背景层次（越靠上越亮） */
  --bg:        #0d1117;   /* 页面底 */
  --surface:   #161b22;   /* 卡片/表格/侧栏 */
  --surface-2: #1c2128;   /* 悬浮/展开行/输入框底 */
  --overlay:   #1c2128;   /* 弹窗底 */

  /* 边框与分割 */
  --border:    #30363d;   /* 主边框 */
  --border-mut:#21262d;   /* 弱分割线 */

  /* 文字 */
  --t1:        #e6edf3;   /* 一级（标题/主要文字） */
  --t2:        #7d8590;   /* 二级（次要/表头） */
  --t3:        #6e7681;   /* 三级（占位/禁用/时间戳） */

  /* 主色（电青，仅用于主按钮/选中/链接/焦点） */
  --primary:   #3b82f6;
  --primary-h: #4c8ef7;   /* hover */
  --primary-bg:#132033;   /* 主色浅底（选中项背景） */

  /* 语义色 + 对应浅底（badge/状态） */
  --green:     #3fb950;  --green-bg:  #12261a;
  --yellow:    #d29922;  --yellow-bg: #251d0e;
  --red:       #f85149;  --red-bg:    #2a1416;
  --blue:      #3b82f6;  --blue-bg:   #132033;
  --gray:      #7d8590;  --gray-bg:   #1c2128;
}
```

用色规则：
- **主色 `--primary` 稀缺使用**：只给主按钮、选中导航、链接、输入框焦点边框。不做大面积填充。
- **状态一律走语义色 badge**：active/published→green，paused/pending→yellow，rejected/danger→red，experiment/发版→blue，archived/baseline→gray。
- 深色下**不用纯黑 #000 文字/边框**，用上表灰阶，避免刺眼与死黑。

## 3. 字体

```css
--font: "PingFang SC","Microsoft YaHei",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
--mono: "SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
```

- 正文 13px / 行高 20px；表格单元 13px；表头 12px。
- 页面标题 16px / 字重 600；卡片小标题 12px / 字重 400 / 用 `--t2`。
- 统计卡数字 24px / 字重 600。
- **等宽字 `--mono` 强制用于**：资产 ID、版本串、KitOps ref、trace ID、时间戳。这是开发者风的核心识别点。

## 4. 尺寸与间距（紧凑高密度）

```css
--radius-sm: 4px;   /* 按钮/badge/输入框 */
--radius:    6px;   /* 卡片/弹窗 */
--row-h:     40px;  /* 表格行高（紧凑） */
--head-h:    36px;  /* 表头行高 */
--ctrl-h:    30px;  /* 按钮/输入框高 */
--gap:       8px;   /* 卡片间距/元素间距 */
--pad-card:  14px;  /* 卡片内边距 */
--pad-cell:  12px;  /* 单元格左右内边距 */
```

- 圆角小（4-6px），**不用 12px 大圆角**（那是亲和风，非开发者风）。
- 阴影极弱或无：卡片靠 `--border` 区分层次，不靠投影。弹窗可用极淡投影 `0 8px 24px rgba(0,0,0,.4)`。
- 布局：顶栏 48px + 左侧导航 200px + 内容区 `--bg`。

## 5. 组件规范

**按钮**
- 主按钮：`--primary` 底、白字、`--radius-sm`、高 `--ctrl-h`、hover→`--primary-h`。
- 默认按钮：`--surface` 底、`--t1` 字、`--border` 边框、hover→`--surface-2`。
- 文字按钮：无底、`--primary` 字（危险动作用 `--red`）。

**表格**（核心组件）
- 表头：`--surface` 底、`--t2` 字、12px、行高 `--head-h`。
- 行：`--surface` 底、行间 `--border-mut` 分割、行高 `--row-h`、hover→`--surface-2`。
- 可点击行 `cursor:pointer`；展开详情行用 `--surface-2` 底。

**Badge / 状态**：小圆角 `--radius-sm`、语义色前景 + 对应 `-bg` 底、12px、内边距 `0 6px`。状态前可加 `●` 圆点强化。

**输入框 / 下拉**：`--surface-2` 底、`--border` 边框、`--t1` 字、`--radius-sm`、高 `--ctrl-h`、焦点→`--primary` 边框。占位符 `--t3`。

**卡片**：`--surface` 底、`--border` 边框、`--radius`、内边距 `--pad-card`。

**弹窗**：遮罩 `rgba(0,0,0,.6)`；弹窗体 `--overlay` 底、`--border` 边框、`--radius`。**禁用原生 confirm/alert**，用自定义弹窗。

**Toast**：右上角、深色底 `--surface-2` + `--border` 边框 + 语义色左边条、2s 自动消失。

**diff 展示**：等宽字、深色代码底（`#0a0d12`），增行 `--green`、删行 `--red`。

## 5.1 图标（Icon）

- 全部使用**单色线性 SVG**（Lucide / Tabler 风格：24×24 viewBox、`stroke` 描边、`fill:none`、圆角线帽）。内联为 `<svg>`，不引外链、不用 emoji、不用图标字体。
- 尺寸：导航 16px、按钮内 14px、标题旁 16px。
- 颜色：默认 `currentColor` 继承文字色（导航默认 `--t2`，选中/hover→`--primary`）。描边宽 1.75。
- 语义要贴切：资产=box、实验=flask/beaker、审核=sparkles、遥测=bar-chart、搜索=search、环境=server。

## 5.2 侧滑抽屉（Drawer）

详情从右侧滑入，替代行内手风琴展开。规范：
- 遮罩 `rgba(0,0,0,.5)`；抽屉从右侧滑入，宽 480px，满高，`--surface` 底、左侧 `--border` 边框。
- 顶部固定标题栏（标题 + 关闭按钮），内容区滚动。
- 动画 `transform:translateX` 0.2s。ESC / 点遮罩关闭。
- 用于：资产的版本列表、实验的 variant 指标、候选的 diff 对比。

## 5.3 统计卡趋势

- 卡片右上角放趋势徽标：`↑12%`（正向 `--green`）/ `↓5%`（负向 `--red`）/ 持平 `--t2`。
- 可选内嵌 mini sparkline：纯内联 SVG 折线，`--primary` 描边、无填充、高 24px。

## 5.4 数据面板

工具栏 + 表格合为一张卡片（`--surface` 底 + `--border` 边框 + `--radius`），形成整体"数据面板"。
- 面板头部：左侧标题/结果计数、右侧筛选与操作。
- 表格无独立边框（并入面板），行分割用 `--border-mut`。
- 内容区加 `max-width:1440px` 居中，避免宽屏下横向拉伸过散。

## 5.5 可排序表头

- 可排序列表头带排序箭头（默认灰 `↕`、升序 `↑`、降序 `↓`，激活列箭头用 `--primary`）。
- 点击切换 升→降→还原三态。hover 表头背景微亮。

## 5.6 结果计数与空态

- 筛选/搜索区显示"共 N 条"；有筛选条件时显示"清空"文字按钮回到全量。
- 空结果：居中图标 + 说明文字 + （若有筛选）"清空筛选"按钮。

## 5.7 加载态（骨架屏）

- 表格加载中显示骨架行：`--surface-2` 底色块 + 微光扫过动画（`@keyframes shimmer`）。
- 骨架行数固定 5 行，列宽与真实表格一致。

## 6. 交互反馈

- 所有可点击元素必须有 hover 态（背景或颜色变化）。
- 状态变更（暂停/恢复/审核）必须即时反映到 UI + Toast 提示。
- 表单必填校验失败：`--red` 内联错误提示 + 阻止提交。
- 删除/归档为逻辑操作，走自定义确认弹窗。

## 7. 禁止项（AI slop 黑名单）

- 紫蓝渐变、装饰性色块/波浪/几何图形。
- 大圆角（>8px）卡片 + 重投影。
- 大面积主色填充。
- Emoji 作为核心视觉元素（导航小图标可用单色字符）。
- 纯白 #fff 底或纯黑 #000（本项目为深色，禁浅色底）。
- lorem ipsum 占位文本，一律用真实业务内容。
