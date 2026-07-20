# AgentMesh Hooks · VS Code 智能体模式接入

> 定位：agentmesh 客户端胶水的**全部**内容。两个 Python 脚本 + 一份 VS Code hook 配置，跑起来靠 `kit CLI` + `python3`。
> 依赖背景：[VS Code Agent Hooks 官方文档](https://code.visualstudio.com/docs/agent-customization/hooks) · [客户端 Pivot 补丁](../docs/plans/2026-07-20-agentmesh-vscode-pivot.md)。

## 1. 目录结构

```
hooks/
├── README.md                     # 本文件
├── config/
│   └── agentmesh.hooks.json      # VS Code hook 注册文件（拷到 .github/hooks/ 即生效）
└── scripts/
    ├── session_start.py          # SessionStart：resolve variant + kit unpack 落盘
    └── stop.py                   # Stop：transcript metadata + POST ingest
```

## 2. 快速安装（3 步）

### 2.1 装依赖

- `python3`（≥ 3.9，官方 hook stdin 是 JSON，脚本零第三方依赖，只用 stdlib）
- [`kit` CLI](https://github.com/kitops-ml/kitops)（KitOps 客户端，用于 `kit unpack`）
- VS Code ≥ 1.104（Agent Hooks Preview 起点）

### 2.2 配置环境变量

在 `~/.zshrc` / `~/.bashrc` 加：

```sh
export AGENTMESH_API="https://agentmesh.internal.example.com"
export AGENTMESH_CLIENT_ID="$(whoami)-$(hostname)"     # GrowthBook 粘性分桶用
export AGENTMESH_TOKEN="<你的内部 token>"                # 中台鉴权
export AGENTMESH_UPLOAD_TRANSCRIPT="false"             # true 才上传会话原文
```

### 2.3 注册 hook 到工作区

```sh
mkdir -p .github/hooks
cp hooks/config/agentmesh.hooks.json .github/hooks/agentmesh.json
```

保存后 VS Code 自动加载，通过 `Developer: Show Agent Debug Logs` 命令查看事件是否触发。

## 3. 事件覆盖

当前只注册 2 个事件，其余 6 个官方事件按需追加：

| 事件 | 脚本 | 作用 |
|---|---|---|
| `SessionStart` | `session_start.py` | 调 `/api/hooks/resolve` → 拿 `{assetId, version, kitRef}` 数组 → `kit unpack` 到 `.github/` → VS Code 热加载 |
| `Stop` | `stop.py` | 读 `transcript_path` → 生成 metadata + 工具调用摘要 → `POST /api/sessions/ingest` |

后续可扩展：
- `PreToolUse`：拦截危险命令（对齐中台策略库）
- `PostToolUse`：文件变更审计
- `UserPromptSubmit`：注入项目上下文 / 记审计

## 4. 中台接口契约（v1）

### 4.1 `POST /api/hooks/resolve`

```jsonc
// 入参
{ "clientId": "payton-mbp", "workspaceRoot": "/Users/payton/ai/agentmesh" }
// 返参
{
  "assignments": [
    { "assetId": "coding-agent", "version": "1.5.0-canary", "kitRef": "zot.example.com/coding-agent:1.5.0@sha256:abc..." }
  ]
}
```

### 4.2 `POST /api/sessions/ingest`

```jsonc
// 入参
{
  "sessionId": "vscode-...",
  "clientId": "payton-mbp",
  "workspaceRoot": "/Users/payton/ai/agentmesh",
  "toolCallsSummary": { "turns": 12, "toolCalls": { "editFiles": 3 }, "sizeBytes": 45120 },
  "transcriptRef": null   // AGENTMESH_UPLOAD_TRANSCRIPT=true 时为本机路径
}
// 返参
{ "ok": true }
```

## 5. 调试与排错

- **看事件是否触发**：VS Code 命令面板 → `Developer: Show Agent Debug Logs`。
- **看 hook 本地日志**：工作区 `.agentmesh/logs/session_start.log` / `stop.log`（脚本自建，含最近失败原因）。
- **hook 一直不生效**：确认 `chat.hookFilesLocations` 设置里包含 `.github/hooks`（默认已开），并且文件名以 `.json` 结尾。
- **kit unpack 失败**：`kit login <registry>` 登录后重试；确保 `AGENTMESH_TOKEN` 与 registry 凭证独立配置。

## 6. 安全说明

- **stdin/stdout JSON**：脚本永不 `exit 2`（阻塞级），失败一律 `exit 0 + continue:true`，避免影响开发者会话。
- **AGENTMESH_TOKEN**：只从环境变量读取，永远不写入日志（脚本已实现）。
- **transcript 上传默认关闭**：`AGENTMESH_UPLOAD_TRANSCRIPT=true` 才上传，且需在中台配合去标识化 pipeline（FR6 · PRD-13）。

## 7. 与老方案对照

| 老方案 | 新方案 |
|---|---|
| `openclaw-agent` Python 包（数百行，管理加载/绑定/记忆） | `hooks/scripts/*.py`（两个短脚本，纯 stdlib） |
| OpenHands Docker 沙箱 | VS Code 官方工具审批 + `PreToolUse` hook 策略拦截 |
| Letta 本地记忆状态 | VS Code Memory 面板；关键片段通过 `Stop` hook 上传 |
| 客户端启动器 | VS Code 打开工作区自动触发 SessionStart |
