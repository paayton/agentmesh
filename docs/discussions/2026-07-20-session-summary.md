# AgentMesh 讨论纪要（2026-07-20）

> 本次会话围绕 AgentMesh 项目的设计架构、Hermes Agent 调研、VS Code 智能体资产扩展、知识库功能定位等主题展开。本文档汇总关键结论，用于指导后续实现。

---

## 1. 项目定位回顾

AgentMesh 是一个面向 **10-100 人小团队** 的私有化 Agent 平台中台，核心价值是：

> 让 prompt/skill/tool 的版本迭代形成"可灰度、可度量、可半自动进化"的闭环。

关键设计决策：
- 客户端采用 **VS Code 智能体模式 + Hooks**，不自建客户端（已 Pivot）。
- 中台采用 **Python + FastAPI**。
- 推理走 **LiteLLM Proxy** 统一路由 Claude/OpenAI/Kimi 等云端厂商。
- 资产分发用 **KitOps OCI ModelKit**。
- 灰度用 **GrowthBook** 多值 flag + client_id 粘性分桶。
- 遥测用 **Langfuse** 自托管。
- 自进化用后端 `hermes-worker` 生成 skill 候选，人工审核后发版。

---

## 2. Hermes Agent 调研结论

### 2.1 Hermes Agent 是什么

Hermes Agent（NousResearch/hermes-agent，MIT 许可证）是一个完整的终端 Agent 框架，特点：
- 自带 self-improving 循环：Act → Evaluate → Reflect → Update
- 有 background review 机制：每轮对话后 fork AIAgent 判断是否创建/更新 skill
- 有 curator 机制：定期审查 agent-created skills，做 stale/archive/consolidate
- 自带 `hermes serve` / `hermes dashboard` 本地网关

### 2.2 能否把 Hermes 代码搬进 agentmesh 的 hermes-worker？

**结论：不建议直接搬代码，但强烈借鉴其设计思想。**

原因：
- Hermes 是单体终端 Agent 操作系统，代码量巨大（核心 Python 几十万行），高度依赖其内部运行时（AIAgent fork、tool 系统、memory manager）。
- AgentMesh 的 hermes-worker 输入是 Langfuse trace 和 session metadata，输出是中台 `skill_candidate` 记录，与 Hermes 的输入输出完全不同。
- 直接集成会导致客户端/中台边界重新模糊，违背 VS Code Pivot 的核心决策。

可借鉴的部分：
- Background review 的触发与 prompt 设计
- Skill 生命周期状态机（active → stale → archived）
- 安全门/审核门设计
- SKILL.md frontmatter 规范

### 2.3 Hermes 是否有开源配套后端？

**结论：没有独立的开源团队后端。**
- Hermes 自带 `hermes serve` / `web_server.py`，但那是单机/单用户网关。
- 官方 Nous Portal 和 Skills Hub 是闭源/托管服务。
- 第三方没有成熟的 Hermes 团队后端开源项目。

这意味着 AgentMesh 要做的"团队级资产分发 + 灰度 + 遥测 + 审核"正好是 Hermes 生态的缺失环节。

### 2.4 Hermes 作为终端是否可行？

**结论：技术上可行，但对 AgentMesh 不合理。**
- 会推翻 VS Code Pivot，重新走回自建客户端的老路。
- 客户端复杂度会从"两份 hook 脚本"膨胀为"完整 Agent OS"。
- 合理做法是把 Hermes 的 self-improving 循环理念放在后端 `hermes-worker`，终端继续用 VS Code。

---

## 3. VS Code Prompt Files 的启示

参考文档：[Use prompt files in VS Code](https://code.visualstudio.com/docs/agent-customization/prompt-files)

关键结论：
- **`.prompt.md` 应作为第四类 VS Code 智能体资产纳入 KitOps ModelKit。**
- 默认位置：`.github/prompts/`，可通过 `chat.promptFilesLocations` 自定义。
- frontmatter 字段（description/name/agent/model/tools）可作为中台资产元数据。
- 支持 `tools` 指定 MCP tools，与 AgentMesh 的 MCP 配置分发能力天然衔接。
- 用户可通过 `/create-prompt` 或从会话提取生成 prompt file，这是 skill 沉淀的另一种形态。

建议更新：
- 架构设计文档 §4.1：资产层增加 `.prompt.md`
- VS Code Pivot 补丁 §6：ModelKit layout 增加 `prompts/` 目录
- PRD：新增 prompt file 资产管理和灰度需求
- `hooks/session_start.py`：增加 `prompts/` 目录 unpack 处理

---

## 4. VS Code 智能体自定义项远程管理分析

基于 VS Code 智能体设置界面的七类自定义项，按"能否通过 KitOps ModelKit + 中台灰度下发"分类：

| 类别 | 文件/形式 | 能否远程管理 | 说明 |
|---|---|---|---|
| 智能体 | `.agent.md` | ✅ 可以 | ModelKit 核心资产 |
| 技能 | `SKILL.md` | ✅ 可以 | ModelKit 核心资产 |
| 指令 | `.instructions.md` | ✅ 可以 | ModelKit 核心资产 |
| Prompt Files | `.prompt.md` | ✅ 可以 | 建议新增为第四类资产 |
| 挂钩 | `hooks.json` | ⚠️ 部分可以 | SessionStart/Stop 等接入 hook 应固定；策略 hook 可远程分发 |
| MCP 服务器 | `.mcp/config.json` | ⚠️ 配置可以 | 配置可分发，但 server 进程需本地/远端实际运行 |
| 插件 | `.vsix` / 扩展市场 | ❌ 不建议 | 走 VS Code 扩展机制，不适合 KitOps |
| 工具 | 内置工具开关 | ❌ 不行 | 运行时设置，非文件资产 |

后台 CRUD 应围绕前五类资产设计，插件和工具开关不纳入 AgentMesh。

---

## 5. 知识库功能定位建议

### 5.1 推荐位置

**新增独立的 `agentmesh-rag` 服务，与 `agentmesh-api` 并列。**

架构：
```
VS Code 客户端
    ↓
agentmesh-api（中台）
    - 知识库管理 API（权限、元数据、转发）
    ↓
agentmesh-rag（新增独立服务）
    - 文档解析 / chunk / embedding
    - 向量检索 / rerank / 混合检索
    - 答案生成 / 引用组装
    ↓
pgvector / Milvus / Weaviate
```

### 5.2 为什么不放在其他地方

- 不放客户端：知识库需要团队共享和长期维护。
- 不放 hermes-worker：它是离线 job，不是在线检索服务。
- 不放中台内部（长期）：向量检索会拖垮中台，扩展性差。
- 不放 KitOps 直接：KitOps 适合不可变资产包，不适合动态检索。

### 5.3 与资产体系打通

- 知识库作为新资产类型，纳入 `asset_version` / `knowledge_base` 表。
- `.agent.md` / `SKILL.md` / `.prompt.md` 的 frontmatter 可声明依赖的知识库。
- 知识库索引可定期打包为 KitOps ModelKit，走版本基线 + 灰度 + 回滚。
- 可通过 GrowthBook 灰度不同版本的知识库或不同检索策略。

### 5.4 MVP 路径

1. 先在 `agentmesh-api` 内新增 rag 模块，直接调 pgvector。
2. 设计时预留拆分接口，未来把 rag 模块拆成独立 `agentmesh-rag` 服务。
3. 核心 API：
   - `POST /api/kb/collections`
   - `POST /api/kb/collections/{id}/ingest`
   - `POST /api/kb/collections/{id}/query`
   - `PATCH /api/assets/{asset_id}/knowledge_bases`

---

## 6. 下一步行动建议

1. 更新架构设计文档：
   - 增加 `.prompt.md` 资产类型
   - 增加知识库服务定位
2. 更新 VS Code Pivot 补丁的 ModelKit layout
3. 更新 PRD，补充 prompt file 和知识库相关需求
4. 更新 `hooks/session_start.py`，支持 `prompts/` 目录 unpack
5. M1 仍优先打通"SessionStart → resolve → kit unpack → Stop → ingest"核心闭环

---

*本文件由 2026-07-20 会话整理生成，用于项目备忘和后续开发参考。*
