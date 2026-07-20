# AgentMesh 客户端方案 Pivot：从 OpenClaw 薄封装到 VS Code 智能体模式

> 生效日期：2026-07-20 · 类型：架构补丁（不重写老文档，作为决策快照）
> 影响文档：[architecture-design](./2026-07-20-agentmesh-architecture-design.md)、[prd](./2026-07-20-agentmesh-prd.md)、[role-touchpoint-matrix](./2026-07-20-agentmesh-role-touchpoint-matrix.md)、[../todos/todolist.md](../todos/todolist.md)
> 触发：VS Code 智能体模式已内置 Agents / Skills / Instructions / Hooks / MCP / Plugins 六类自定义位（[官方文档](https://code.visualstudio.com/docs/agent-customization/hooks)），原方案「OpenClaw = 薄封装 OpenHands/Aider」的绝大多数职责被 VS Code 收编。

## 1. 决策一句话

**放弃自建客户端 OpenClaw**，直接把 VS Code 智能体模式当客户端；agentmesh 收缩定位为「VS Code 智能体资产的**灰度分发 + 度量 + 半自动进化**回路」，与 VS Code 共生，不再包住它。

## 2. 为什么改（3 条硬理由）

1. **VS Code 原生覆盖了 §4.1 L1 执行层与客户端胶水的绝大部分**：
   - Agent 定义 → `.agent.md`（frontmatter + prompt）
   - Skill → `SKILL.md`（路由到详细指令）
   - Prompt/Instruction → `.instructions.md`（含 `applyTo` glob 精准触发）
   - Tool 层 → 官方 MCP 配置（`.mcp/config`、`~/.copilot/mcp.json`）
   - 生命周期埋点 → 官方 Hooks（8 个事件）
   - Plugin 打包分发 → 官方 Plugins（打包 hooks + skills + instructions + agents）
2. **Hooks 完全能承接原 `openclaw-agent` 的所有职责**：`SessionStart` 拉资产、`UserPromptSubmit` 审计、`PreToolUse` 拦截、`PostToolUse` 打点、`Stop` 上传会话。stdin 里官方给 `session_id / transcript_path / cwd / tool_name / tool_input`，直连中台足够。
3. **零开发跑起来**：删掉 OpenClaw 的加载器 / Docker 沙箱依赖 / OpenHands + Aider + Letta 三方 SDK 接线，M0 阻塞项少一个，客户端形态从「装容器 + 装 CLI + 装 agent」变成「装 VS Code + 拷两份 hook 文件」。

## 3. 定位调整（一句话对齐）

| 项 | 旧定位 | 新定位 |
|---|---|---|
| 客户端 | OpenClaw = 薄封装 OpenHands + Aider + Letta，Python 中量胶水 | **VS Code 智能体模式**（零开发），只加两份 hook 脚本 |
| 中台价值 | 「让本地 agent 跑起来 + 分发资产」 | **只做灰度 + 度量 + 审核 + 半自动进化**（VS Code 已解决"跑起来"）|
| 资产内容 | KitOps ModelKit 里塞 prompt/skill/tool（自定义 layout） | KitOps ModelKit 里塞 **VS Code 官方文件格式**（`.agent.md` / `SKILL.md` / `.instructions.md` / `hooks.json` / mcp 配置），pull 下来直接落盘生效 |
| 记忆层 | Letta 本地记忆状态 | VS Code 内置 Memory 面板 + hooks 上传关键片段回中台（Letta 从核心组件降为**可选**）|
| 沙箱 | OpenHands Docker 沙箱 | VS Code 智能体审批 + hooks `PreToolUse` 策略拦截（团队自用场景够）|

## 4. 新客户端形态

```
开发者本机（macOS / Linux / WSL）
└── VS Code + 智能体模式
    ├── .github/hooks/agentmesh.json     ← 生命周期埋点（工作区级，跟仓库走）
    │     ├─ SessionStart  → 拉 variant + pull ModelKit → 落盘（触发热加载）
    │     ├─ UserPromptSubmit → 记审计（可选：注入项目上下文）
    │     ├─ PreToolUse    → 危险命令拦截（复用中台策略）
    │     ├─ PostToolUse   → 变更文件记录
    │     └─ Stop          → transcript_path 打包 + trace 回灌 + 沉淀候选 skill
    ├── .github/agents/*.agent.md         ← 由 KitOps ModelKit 分发进来
    ├── .github/skills/*/SKILL.md         ← 由 KitOps ModelKit 分发进来
    ├── .github/instructions/*.instructions.md
    └── .mcp/config.json                  ← MCP server 目录（可由 ModelKit 分发）
```

- **热加载**：VS Code 检测到这些文件变动自动生效，SessionStart hook 落盘后无需重启。
- **一份 hook 跨客户端**：VS Code、Claude Code、Copilot CLI 共用同一 JSON 格式（官方明确），未来切客户端零迁移成本。

## 5. 客户端 ↔ 中台胶水从"中"缩到"小"

| 模块 | 旧 | 新 |
|---|---|---|
| `openclaw-agent`（Python 中量） | 加载/绑定/埋点/记忆接线/回退状态机 | **删除** |
| **`agentmesh-hooks`（Python 小量）** | — | 两个脚本：`session_start.py`、`stop.py`；纯 stdin/stdout + HTTP，无 SDK 依赖 |
| `agentmesh-api` 新增接口 | — | `POST /api/hooks/resolve`、`POST /api/sessions/ingest`（详见 §7）|

胶水量从原架构 §4.6 的 5 项 → **3 项**（`agentmesh-hooks` + `agentmesh-api` + `hermes-worker` + React 后台 + 版本命名约定），且客户端那一格从「中」降到「小」。

## 6. ModelKit 内容 layout（对齐 VS Code 面板）

KitOps 打的 ModelKit `pull` 下来后直接展开进 `.github/`，layout：

```
modelkit/
├── agents/
│   └── coding.agent.md            # VS Code Agents 面板
├── skills/
│   └── refactor/SKILL.md          # VS Code Skills 面板
├── instructions/
│   └── style.instructions.md      # VS Code Instructions 面板（含 applyTo）
├── hooks/
│   └── policy.hooks.json          # 追加型 hooks（与工作区 agentmesh.json 合并）
├── mcp/
│   └── servers.json               # MCP server 目录
└── manifest.yaml                  # KitOps 原生 manifest（版本、依赖、digest）
```

**优势**：VS Code 智能体自定义面板里那 6 类每一项都对得上一个目录，运营人员看后台版本 = 看 VS Code 面板加载了哪些资产，心智一致。

## 7. 中台接口增量（补丁到 architecture-design §4.4）

新增 2 个客户端 hook 专用接口（camelCase 走前端契约，snake_case 走 hook stdin 契约）：

| 路径 | 方法 | 触发方 | 功能 |
|---|---|---|---|
| `/api/hooks/resolve` | POST | `SessionStart` hook | 入参 `{client_id, workspace_root, asset_ids?}` → 查 GrowthBook → 返 `{assignments: [{asset_id, version, kit_ref}]}`；hook 据此 `kit unpack` 到 `.github/` |
| `/api/sessions/ingest` | POST | `Stop` hook | 入参 `{session_id, client_id, variant_bindings, transcript_ref, tool_calls_summary, feedback?}` → 中台存会话 metadata + 转 Langfuse trace |

**为何不复用 `/api/assets/resolve`**：老接口一次一个 asset，SessionStart 通常要一把拉齐一个工作区绑定的多资产；`/api/hooks/resolve` 做批量优化并附带工作区标识，语义更贴 hook。老接口保留供后台/CLI 用。

## 8. 数据边界修订（对齐 §6.2）

新客户端不带 Docker 沙箱、不落 Letta 本地状态，数据流有 2 处变化：

1. **推理路径不变**：VS Code 智能体本身通过 GitHub Copilot 或用户配置的 LM Provider 走出境；agentmesh 若强制走自家 LiteLLM Proxy，需要在 hooks / MCP 侧注入 API base（写入 `Config.overrides`）。**这一条留作 M0 阻塞项：确认 VS Code 智能体是否支持 base URL 覆盖**。
2. **会话内容边界**：`transcript_path` 可能含原始对话。默认策略——`Stop` hook **只把 metadata + tool_calls 摘要** POST 到中台，`transcript` 原文默认留在本机；若用户在 VS Code 「设置 → agentmesh.uploadTranscript = true」显式开启，才上传。这是 FR6 「回流去标识化」在客户端侧的具体承接点。

## 9. 影响面清单（下一步改动依据）

| 目标文件 | 改动类型 | 要点 |
|---|---|---|
| [architecture-design.md](./2026-07-20-agentmesh-architecture-design.md) §4.1 | 替换 | L1 执行层 = VS Code Agent Mode + Hooks；OpenHands/Aider/Letta 从核心组件降为可选 |
| 同上 §4.4 | 增补 | 新增 §7 两个接口 |
| 同上 §4.5 | 替换第 3 步 | 「openclaw-agent 启动/定时」→「SessionStart hook」|
| 同上 §4.6 | 替换 | `openclaw-agent` → `agentmesh-hooks`，规模降一档 |
| 同上 §6.1 | 替换客户端块 | 删掉 OpenHands/Aider/Letta/openclaw-agent，改为 VS Code + hooks |
| 同上 §8 | 增补 | 新增未决项：VS Code 智能体 LM base URL 覆盖机制 |
| [prd.md](./2026-07-20-agentmesh-prd.md) §2 | 替换 | 角色①的触点从「OpenClaw 客户端」改为「VS Code 智能体模式」|
| 同上 PRD-01/PRD-11/PRD-13 | 微调 | 触点换名，功能不变 |
| [role-touchpoint-matrix.md](./2026-07-20-agentmesh-role-touchpoint-matrix.md) §2.① | 替换 | 触点名称、页面位置换成 VS Code 面板 |
| [../todos/todolist.md](../todos/todolist.md) | 增删条目 | 删 `openclaw-agent` 相关；新增 `agentmesh-hooks` M1 落地条目 |
| `hooks/` 新目录 | 新增 | 最小可运行样例（见 §10）|

## 10. 落地样例（M1 前置最小竖切）

新增仓库目录：

```
hooks/
├── README.md                     # 安装/调试说明（含 chat.hookFilesLocations 配置）
├── config/
│   └── agentmesh.hooks.json      # VS Code 官方格式，注册 SessionStart + Stop 两个事件
└── scripts/
    ├── session_start.py          # 调 /api/hooks/resolve → kit unpack 到 .github/
    └── stop.py                   # 读 transcript_path → POST /api/sessions/ingest
```

安装方式：把 `hooks/config/agentmesh.hooks.json` 拷贝到 `.github/hooks/agentmesh.json`，VS Code 自动加载。

## 11. 风险与回退

| 风险 | 缓解 | 回退路径 |
|---|---|---|
| VS Code 智能体不支持 LM base URL 覆盖 → 走不通中台 LiteLLM Proxy | M0 前 spike 验证；不通则 hooks 侧不做模型路由，中台 Proxy 降级为"只做审计与限流的旁路" | 保留 L1 备胎：`agentmesh-cli`（Python，纯 CLI，绕过 VS Code） |
| Hooks preview 期字段变更 | 只使用官方文档中"stable"字段（session_id / cwd / transcript_path / tool_name / tool_input），避开 hookSpecificOutput 的实验字段 | 配置文件按事件粒度隔离，字段变更单点修 |
| 会话 transcript 含机密 | 默认不上传原文，只上传 metadata；开启回流走 §8 显式授权 + 去标识化 | 关闭 `uploadTranscript` 即回退到纯 metadata |
| 团队已有非 VS Code 用户（如 JetBrains） | 保留 Claude Code CLI 与 Copilot CLI 兼容（同一份 hooks.json 通用） | JetBrains 用户走 CLI 客户端，同 hook 脚本 |

## 12. 里程碑重排

- **M0** 新增阻塞项：VS Code 智能体 LM base URL 覆盖机制实测（1 天内可判定）。
- **M1** 关键路径改为：`agentmesh-hooks` 两个脚本 + 中台 `/api/hooks/resolve` + `/api/sessions/ingest`，客户端零装机（只放两份文件）。
- **M2+ 及以后不变**：后台 CRUD、Hermes 自进化、审核发版、回流共享。

---

**结论**：这次 pivot 让 agentmesh 从"想覆盖 agent 全栈"回到"只做别人不做的那段（灰度 + 度量 + 进化回路）"，符合最小胶水原则；客户端形态归零到 VS Code 官方能力上，M1 竖切的开发量再降一档。
