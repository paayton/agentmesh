# AgentMesh 整体架构设计

> 本文基于选型调研 [docs/research/2026-07-20-local-first-agent-platform-oss-stack.md](../research/2026-07-20-local-first-agent-platform-oss-stack.md) 与需求 [requirements.md](../../requirements.md)。
> 无既有代码仓库，本方案为**全新设计（greenfield）**，不涉及现有代码对齐。
>
> **⚠ 2026-07-20 客户端 Pivot**：客户端方案已从「OpenClaw 薄封装 OpenHands/Aider」调整为「**VS Code 智能体模式 + Hooks**」，详见补丁文档 [2026-07-20-agentmesh-vscode-pivot.md](./2026-07-20-agentmesh-vscode-pivot.md)。本文正文按补丁增量更新，历史决策以补丁文档为准。

## 1. 背景与目标

做一个**本地优先、资产云端分发、可自进化、支持版本灰度实验的私有化 Agent 平台**（暂名 AgentMesh），目标用户是 10-100 人的小团队内部，偏 coding assistant 但要覆盖运营 / 系统排障 / 日常业务操作等泛工程场景。

MVP 目标：**用最小开发量跑通"本地执行 → 云端资产 → 技能沉淀 → 灰度迭代"闭环**。

### 关键决策（已与用户确认）

| 决策项 | 选择 | 影响 |
|---|---|---|
| 技术栈 | **Python + FastAPI**（中台/胶水），React（后台前端） | 中台仍用 Python，客户端零开发；LiteLLM SDK 直连 |
| 自进化程度（FR5） | **半自动**：生成候选 → 审核 → 发版 | Hermes 只产候选，Control Plane 提供审核工作流 |
| MVP 定位 | **团队自用** | 不做多租户/组织隔离/品牌抽象，架构最简 |
| 客户端形态 | **VS Code 智能体模式 + Hooks**（Pivot 后） | 官方内置 Agents/Skills/Instructions/Hooks/MCP/Plugins；agentmesh 只发资产 + 拉指标，客户端零装机 |

## 2. 需求范围

### 2.1 MVP 功能

- FR1 多厂商云端 LLM 推理（中台自托管 LiteLLM Proxy 统一路由 Claude/OpenAI/Kimi 等，集中管密钥 + 成本/限流/审计）
- FR2 标准化 Agent 资产分发（KitOps OCI ModelKit：prompt/skill/tool/workflow）
- FR3 版本基线与灰度实验（GrowthBook 多值 flag + client_id 粘性分桶 → 绑定 asset 版本）
- FR4 运行中沉淀 skill（Letta 记忆 + 本地 skill 文件，默认不上传）
- FR5 技能半自动自进化（Hermes 生成候选 → 后台审核 → KitOps 发新版）
- FR6 技能共享回流（显式授权上传去标识化 skill 到 ClawHub）
- FR7 运营后台（资产/实验/遥测/skill 回流查看 + 审批发版）

### 2.2 非功能需求

平台自身数据私有自托管（NFR1，见下）、可私有化部署（NFR2）、最小胶水（NFR3）、许可证 MIT/Apache-2.0/BSD 避免 GPL（NFR4）、可扩展到 1000+（NFR5）。

> **NFR1 修正（数据边界调整）**：本平台采用**纯云端多厂商推理**，推理数据（prompt/代码/上下文）会经中台 LiteLLM Proxy 出境到所选 LLM 厂商（Claude/OpenAI/Kimi 等）——这是使用商业模型的必然。数据边界因此调整为：**平台自身的资产/实验/遥测/审核数据全部私有自托管，不进第三方 SaaS；推理内容按厂商 API 出境，密钥由中台集中托管不下发客户端。** 原"数据不出本地 / 气隙 / 弱网离线"约束（旧 NFR1/NFR6）已废止。

### 2.3 排除项（本期不做）

- 多租户 / 组织级隔离（团队自用，明确不做）
- 品牌可配置 / 一键交付打包（非团队自用场景需求）
- 全自动 skill 改写（选半自动，规避劣化不可追溯风险）
- L1 自建执行器抽象（薄封装，直接复用 OpenHands/Aider）
- Unleash（**许可证排除**：v8.0.0 起 AGPLv3，踩 GPL 红线）

## 3. 现有代码基线

**无代码仓库。** 当前目录仅含 `docs/`，无任何 stack marker（package.json/pyproject.toml/go.mod 等）。本方案所有数据模型、接口、逻辑均标注为**全新设计**，理由统一为：项目从零起步，无可复用/扩展的既有实现。后续迭代须回填本章并遵循增量设计原则。

## 4. 技术方案

### 4.1 架构设计

四层定位映射到开源组件（方框内为**开源件**，`〔〕`内为**要自己写的胶水**）：

```
┌─────────────────────────────────────────────────────────────────────┐
│  VS Code 智能体模式 · 本地客户端（开发者本机）                            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Agents │ Skills │ Instructions │ Hooks │ MCP │ Plugins        │  │
│  │  (.agent.md)(SKILL.md)(.instructions.md)(hooks.json)(mcp cfg)  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│      ↑ VS Code 热加载                        〔agentmesh-hooks〕 Python │
│      │ pull 落盘 .github/                    - SessionStart: 拉 variant │
│      │                                        + kit unpack 到 .github/  │
│      │                                      - UserPromptSubmit: 审计    │
│      │                                      - PreToolUse: 策略拦截      │
│      │                                      - Stop: transcript 打包     │
│      │                                        + trace/session 回灌      │
│      │                                                                  │
│      │  (推理路径: VS Code LM Provider → 可选走中台 LiteLLM Proxy)      │
│      ▼                                                                  │
│   〔中台 LiteLLM Proxy〕统一路由 Claude/OpenAI/Kimi，集中管密钥+成本+限流  │
└───────┬───────────────────────────────────┬────────────────┬─────────┘
        │ pull 资产(OCI)                      │ 取 flag        │ trace
        ▼                                     ▼                ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐  ┌──────────────┐
│ ClawHub · 资产仓库 │  │ Control Plane 中台 │  │ GrowthBook  │  │  Langfuse    │
│ ┌─────────────┐ │  │ 〔agentmesh-api〕 │  │ (L3 灰度)    │  │ (L4 遥测/MIT) │
│ │OCI Registry │ │  │  FastAPI          │  │  MIT        │  │              │
│ │(存 ModelKit)│ │  │  - 资产/实验编排   │  │ variant→版本 │  │ 成功率/时延/  │
│ └─────────────┘ │  │  - skill 回流审核  │  └─────────────┘  │ 反馈 按       │
│ ┌─────────────┐ │  │  - 审批发版(FR7)  │                    │ variant 聚合 │
│ │MCP Registry │ │  │  React 运营后台   │  ┌─────────────┐   └──────────────┘
│ │(工具目录)    │ │  └────────┬─────────┘  │  Hermes     │
│ └─────────────┘ │           │             │ 〔自进化 job〕│
└─────────────────┘           └── 触发候选 ──│ Letta轨迹→   │
                                              │ skill 候选   │
                                              └─────────────┘
```

**组件边界（谁负责什么，绝不越界）：**

| 层 | 组件 | 许可证 | 职责 | 边界（不做什么） |
|---|---|---|---|---|
| L1 执行 | **VS Code 智能体模式** | 官方 | Agents / Skills / Instructions / MCP 加载 + 执行；审批与工具沙箱由 VS Code 官方处理 | agentmesh 不改客户端；只通过 hooks + 官方文件格式介入 |
| L1 埋点 | 〔**agentmesh-hooks**〕 | 自写 | 两个 Python 脚本承接 `SessionStart` + `Stop`（可扩展 UserPromptSubmit/PreToolUse） | 只做拉资产/回灌，不做模型路由 |
| L1 模型 | **LiteLLM Proxy** | MIT | 中台自托管，统一路由 Claude/OpenAI/Kimi 等云端厂商；集中管密钥+成本+限流+审计 | 跨层唯一模型缝；能否强制 VS Code 走 Proxy 见 §8 未决项 |
| L2 资产 | **KitOps** | Apache-2.0 | OCI ModelKit 打包 VS Code 官方格式文件（.agent.md / SKILL.md / .instructions.md / hooks.json / mcp cfg），SHA-256 不可变 | 不做灰度、不做发现 |
| L2 工具 | **MCP Registry**（可选） | MIT→Apache | MCP server/tool 目录（自托管 Go+PG） | preview 版；只管工具发现 |
| L2 应用 | Dify DSL（可选） | — | workflow 应用级 YAML 打包 | 与 KitOps 互补，非必需 |
| L3 灰度 | **GrowthBook** | MIT | 多值 flag + client_id 粘性分桶 → 返回版本串 | 不管资产内容，只返版本号 |
| L4 遥测 | **Langfuse** | MIT | trace/评估/prompt 管理，可气隙 | 数据自托管不出网 |
| L5 记忆 | **VS Code Memory 面板** + Letta（可选） | 官方 / Apache-2.0 | VS Code 内置 Memory 承担会话记忆；Letta 降级为可选深度记忆组件 | agentmesh 只通过 hooks 上传关键片段回中台 |
| 中台 | 〔**agentmesh-api**〕 | 自写 | 资产/实验编排、审核、发版、后台 + hooks resolve/ingest | FastAPI，见 §4.4 |
| 自进化 | 〔**hermes-worker**〕 | 自写 | Langfuse trace + 会话 ingest → skill 候选 | 只产候选，不自动生效 |

**架构决策取舍：**

- **VS Code 智能体模式 vs 自建 OpenClaw 薄封装**：选 VS Code。官方已内置 Agents/Skills/Instructions/Hooks/MCP/Plugins 六类自定义位，覆盖客户端全部胶水；agentmesh 收缩到"发资产 + 拉指标 + 审核候选"回路，客户端零装机、零维护。原 OpenHands + Aider + Letta 三方 SDK 接线全部删除。见 [vscode-pivot 补丁](./2026-07-20-agentmesh-vscode-pivot.md)。
- **KitOps(OCI) vs 自建 zip+manifest**：选 KitOps。需求 FR2 要"版本化包 + manifest"，KitOps 的 OCI ModelKit + SHA-256 不可变摘要天然满足版本基线，且能复用任意现成 registry（Harbor/Zot/GHCR），零额外存储服务。ModelKit 里塞的就是 VS Code 官方文件格式（`.agent.md` / `SKILL.md` / `.instructions.md` / `hooks.json` / mcp cfg），pull 后直接落盘 `.github/` 生效。
- **GrowthBook 返回"版本串"而非布尔**：这是 L3↔L2 接线的核心，见 §4.5。
- **Python + FastAPI 中台**：中台、Hermes、hooks 脚本全 Python，LiteLLM SDK 直连；无跨语言 HTTP 胶水。

### 4.2 核心数据流

**主闭环：本地执行 → 云端资产 → 技能沉淀 → 灰度迭代**

```
① 会话启动（灰度绑定 + 资产加载）
   VS Code SessionStart hook ──client_id──► agentmesh-api /api/hooks/resolve
                            ↓
                    GrowthBook SDK ──► variant 版本串 "coding@1.5.0-canary"
                            ↓
                    返 [{asset_id, version, kit_ref}]
                            ↓
   session_start.py ──kit unpack <kit_ref>──► ClawHub OCI Registry
                    ──落盘到 .github/──► VS Code 热加载 Agents/Skills/Instructions/MCP
   (命中本地缓存则跳过拉取；无缓存回退 baseline 版本)

② 执行（VS Code 智能体模式，云端多厂商推理）
   VS Code Agent ──► LM Provider ──► Claude / OpenAI / Kimi 等厂商
                 （可选：M0 spike 验证能否强制走中台 LiteLLM Proxy 集中管密钥）
                 ──PostToolUse hook──► 记文件变更 / 命令审计
                 ──trace(含 variant 标签)──► Langfuse（自托管）

③ 技能沉淀（本地）
   Stop hook ──读 transcript_path──► 提取可复用 skill 候选
             ──默认仅 metadata──► POST /api/sessions/ingest
   （原始对话默认留本机；显式开启 uploadTranscript 才上传，FR4/FR6）

④ 自进化（半自动）
   hermes-worker ──读 Langfuse 轨迹 + /api/sessions 记录 + 反馈──► 生成 skill 改进候选
                 ──POST /api/skills/candidates──► agentmesh-api（状态=pending）

⑤ 审核发版（FR7）
   运营 ──React 后台──► 审核候选 ──approve──► agentmesh-api
        ──kit pack + push 新版本──► ClawHub ──► 在 GrowthBook 建/调实验 variant
   （新版本进入 ① 的灰度池，闭环成立）

⑥ 回流共享（显式授权，FR6）
   用户 ──VS Code 设置 uploadTranscript=true──► Stop hook 去标识化 skill 上传
   （默认关闭；上传内容不含原始对话）
```

### 4.3 数据模型变更

中台自身状态用 **SQLite（MVP）/ 可平滑迁 MySQL**。GrowthBook/Langfuse/KitOps 各自带存储，中台**不重复存**它们的数据，只存"编排/审核/映射"这层薄状态。全部为**全新设计**（无既有库）。

下列 DDL 遵循团队 MySQL 规范（小写、NOT NULL DEFAULT、ctime/mtime、InnoDB、逻辑删除）：

```sql
-- 资产版本映射表：把 GrowthBook variant 版本串 ↔ KitOps ref 绑定（全新设计）
CREATE TABLE `asset_version` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
  `asset_id` varchar(64) NOT NULL DEFAULT '' COMMENT '资产逻辑ID,如 coding-agent',
  `version` varchar(64) NOT NULL DEFAULT '' COMMENT '版本串,如 1.5.0-canary',
  `kit_ref` varchar(200) NOT NULL DEFAULT '' COMMENT 'KitOps OCI 完整 ref(含 digest)',
  `channel` tinyint NOT NULL DEFAULT 0 COMMENT '通道:0=baseline,1=latest,2=experiment',
  `is_deleted` tinyint NOT NULL DEFAULT 0 COMMENT '是否删除',
  `ctime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `mtime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_asset_version` (`asset_id`,`version`),
  KEY `ix_mtime` (`mtime`)
) ENGINE=InnoDB COMMENT='资产版本↔KitOps ref 映射表';

-- 实验表：镜像 GrowthBook 实验的中台侧元数据(便于后台聚合,不存分流逻辑)（全新设计）
CREATE TABLE `experiment` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
  `gb_experiment_key` varchar(128) NOT NULL DEFAULT '' COMMENT 'GrowthBook 实验 key',
  `asset_id` varchar(64) NOT NULL DEFAULT '' COMMENT '关联资产ID',
  `name` varchar(128) NOT NULL DEFAULT '' COMMENT '实验名称',
  `status` tinyint NOT NULL DEFAULT 0 COMMENT '状态:0=active,1=paused,2=archived',
  `is_deleted` tinyint NOT NULL DEFAULT 0 COMMENT '是否删除',
  `ctime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `mtime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gb_experiment_key` (`gb_experiment_key`),
  KEY `ix_mtime` (`mtime`)
) ENGINE=InnoDB COMMENT='实验元数据镜像表';

-- skill 改进候选表：Hermes 产出、等待审核（全新设计）
CREATE TABLE `skill_candidate` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
  `asset_id` varchar(64) NOT NULL DEFAULT '' COMMENT '关联资产ID',
  `base_version` varchar(64) NOT NULL DEFAULT '' COMMENT '基于哪个版本改进',
  `skill_name` varchar(128) NOT NULL DEFAULT '' COMMENT 'skill 名称',
  `status` tinyint NOT NULL DEFAULT 0 COMMENT '状态:0=pending,1=approved,2=rejected,3=published',
  `reviewer` varchar(64) NOT NULL DEFAULT '' COMMENT '审核人',
  `source_trace_id` varchar(128) NOT NULL DEFAULT '' COMMENT '来源 Langfuse/Letta 轨迹ID',
  `diff_content` text COMMENT 'skill 改进内容/diff',
  `reject_reason` text COMMENT '驳回原因',
  `is_deleted` tinyint NOT NULL DEFAULT 0 COMMENT '是否删除',
  `ctime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `mtime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `ix_asset_id` (`asset_id`),
  KEY `ix_status` (`status`),
  KEY `ix_mtime` (`mtime`)
) ENGINE=InnoDB COMMENT='skill 改进候选表';
```

> 说明：**不建 asset 内容表**——资产内容由 KitOps/OCI registry 存，中台只存 ref 映射，避免与 KitOps 职责重叠（"为何不另建"：内容不可变性、去重、选择性拉取 KitOps 已解决，重存是反模式）。

### 4.4 接口设计（全新设计）

中台 `agentmesh-api`（FastAPI）。前端 React 后台走 camelCase，Schema 用 CamelModel 基类做 camelCase↔snake_case 转换。核心接口：

**资产与版本解析（供客户端）**
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/assets/resolve` | POST | 入参 `{clientId, assetId}` → 查 GrowthBook variant → 返 `{version, kitRef}`（供 CLI/后台单资产调用；hook 场景推荐用批量 `/api/hooks/resolve`） |
| `/api/assets` | GET | 列表：资产 + 各版本/通道（分页、按 assetId 筛选） |
| `/api/assets/{assetId}/versions` | GET | 某资产全部版本 |
| `/api/assets/{assetId}/baseline` | PATCH | 入参 `{version}`：将胜出 variant 提为新 baseline（移动 floating tag 指针，见 §4.8），旧 baseline 降为 latest。供遥测页"提为 baseline"调用（PRD-09） |

**VS Code Hooks 专用接口（Pivot 后新增，见 [vscode-pivot 补丁](./2026-07-20-agentmesh-vscode-pivot.md) §7）**
| 路径 | 方法 | 触发方 | 功能 |
|---|---|---|---|
| `/api/hooks/resolve` | POST | `SessionStart` hook | 入参 `{clientId, workspaceRoot, assetIds?}` → 批量查 GrowthBook → 返 `{assignments:[{assetId, version, kitRef}]}`；hook 据此 `kit unpack` 到 `.github/` |
| `/api/sessions/ingest` | POST | `Stop` hook | 入参 `{sessionId, clientId, variantBindings, transcriptRef?, toolCallsSummary, feedback?}` → 中台存会话 metadata + 转 Langfuse trace；`transcriptRef` 默认不含原文，走显式授权才上传 |

**实验管理（FR3，后台 CRUD）**
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/experiments` | GET | 列表（分页、按 status/assetId 筛选、关键词） |
| `/api/experiments` | POST | 新建：写 GrowthBook 实验 + 本地镜像；variant 关联资产版本 |
| `/api/experiments/{id}` | GET | 详情（含各 variant 版本 + Langfuse 聚合指标） |
| `/api/experiments/{id}` | PUT | 编辑：名称、流量比例、variant→版本 绑定（全可编辑字段） |
| `/api/experiments/{id}/status` | PATCH | active/paused/archived 切换 |
| `/api/experiments/{id}` | DELETE | 逻辑删除（is_deleted=1）+ GrowthBook 侧归档 |

**skill 候选审核（FR5/FR7）**
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/skills/candidates` | GET | 候选列表（按 status/assetId 筛选） |
| `/api/skills/candidates` | POST | Hermes 提交候选（status=pending） |
| `/api/skills/candidates/{id}` | GET | 详情（含 diff 回显、来源轨迹） |
| `/api/skills/candidates/{id}/approve` | POST | 审核通过 → 触发 kit pack+push 新版本 → 建实验 |
| `/api/skills/candidates/{id}/reject` | POST | 驳回（带 reject_reason） |

**遥测代理（FR7 后台展示）**
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/metrics/experiment/{id}` | GET | 从 Langfuse 按 variant 拉成功率/时延/反馈聚合（含 👍/👎 计数，PRD-07） |
| `/api/metrics/candidates/pass-rate` | GET | 候选通过率 + 待审积压统计（按时间窗聚合 skill_candidate 状态，PRD-08） |
| `/api/feedback` | POST | 客户端回灌 👍/👎 反馈：入参 `{clientId, traceId, variant, score, reason?}` → 打 variant 标签入 Langfuse（PRD-07，自进化燃料源头） |

> 前端确认弹框用组件（禁原生 confirm/alert），错误提示用 message 组件。删除均为逻辑删除，KitOps 已发布版本不可删（不可变基线）。

### 4.5 L3 灰度 flag ↔ 资产版本 接线（闭环核心）

**错位**：GrowthBook 原生模型是"flag→布尔/多值→代码分支"，我们要"按流量把 client 稳定绑定到某 **asset 版本** → 拉取加载"。

**桥接（4 步，GrowthBook 原语足够）：**
1. **多值 flag 承载版本串**：GrowthBook experiment 的每个 variant 值 = 资产版本串（如 `coding-agent@1.5.0-canary`），非布尔。
2. **一致性哈希粘性分桶**：GrowthBook 按 `client_id` 做百分比 rollout 且稳定分桶，天然满足 FR3"同 client 多次请求绑定同 variant"，**不用自写哈希**。
3. **客户端胶水（要写）**：VS Code `SessionStart` hook → 传 client_id + workspaceRoot 调 `/api/hooks/resolve` → 拿到 `{assetId, version, kitRef}` 数组 → `kit unpack <kitRef>` → 落盘到 `.github/agents/`、`.github/skills/`、`.github/instructions/`、`.mcp/config.json` → VS Code 热加载。失败回退 baseline。
4. **实验回灌 Langfuse**：`Stop` hook 把 variant 值作为 trace 维度标签打回，成功率/时延/反馈按 variant 聚合，实验结论直接在 Langfuse 看，无需自建统计后端。

### 4.6 要自己写的最小胶水模块清单

| 模块 | 语言 | 职责 | 规模 |
|---|---|---|---|
| `agentmesh-hooks` | Python | 两个脚本：`session_start.py` 调 resolve + kit unpack 落盘；`stop.py` 读 transcript + POST ingest。纯 stdin/stdout + HTTP，无 SDK 依赖 | 小，客户端唯一胶水 |
| `agentmesh-api` | Python/FastAPI | §4.4 全部接口 + SQLite 状态 + 调 GrowthBook/KitOps/Langfuse SDK | 中，中台核心 |
| `hermes-worker` | Python | 读 Langfuse trace + `/api/sessions` 记录 + 反馈 → LLM 生成 skill 候选 → 提交待审 | 小-中，定时 job |
| React 运营后台 | TS/React | 资产/实验/候选审核/遥测 4 个页面 | 中 |
| 版本命名约定 | 约定 | `<asset_id>@<semver>[-channel]` ↔ KitOps ref 解析规则 | 小，一处约定 |

> 除此之外全部复用开源件（VS Code 自身承担 L1 执行）。胶水集中在两条缝：**L3→L2（flag→版本→pull）** 与 **L2→VS Code（ModelKit→`.github/` 落盘热加载）**。

### 4.7 状态流转

**skill 候选**：`pending`(Hermes 产) → `approved`(审核通过) → `published`(已发版进灰度池) ／ `rejected`(驳回带原因)

**实验**：`active`(分流中) → `paused`(暂停) → `archived`(归档，胜出 variant 可提为新 baseline)

### 4.8 版本命名约定（定稿，解锁 M1 resolve 链路）

> 对应 §8 未决项①。决策：**channel 编进 tag**（floating tag 指针方案，兼顾"channel 可读"与"内容不可变"）。

**命名规则**：资产版本串 `<asset_id>@<semver>[-<channel>]`，映射到 KitOps OCI 坐标 `<registry>/<asset_id>:<tag>@<digest>`。

**两类 tag，职责分离：**

| tag 类型 | 例 | 可变性 | 含义 |
|---|---|---|---|
| **不可变版本 tag** | `coding-agent:1.5.0` | 固定绑定一个 digest，永不移动 | 内容真身，`kit pack+push` 时生成，对应 `asset_version.kit_ref`（含 digest） |
| **floating channel tag** | `coding-agent:baseline` / `:latest` / `:canary` | 可移动指针，指向某个不可变版本 tag 的 digest | 灰度通道，"提为 baseline" = 把指针移到新 digest，**内容不变** |

**resolve 解析规则（`/api/assets/resolve`）：**
1. `{clientId, assetId}` → GrowthBook 按 client_id 粘性分桶 → 返 variant 值（如 `coding-agent@1.5.0-canary`）。
2. 中台按 variant 值查 `asset_version`：优先精确匹配 `version`；若 variant 值带 channel 后缀（`-canary`/`-baseline`），则解析 floating tag 当前指向的 digest。
3. 返 `{version, kitRef}`，kitRef 为**含 digest 的完整不可变 ref**（客户端始终 pull 到确定内容，即使 floating tag 之后移动，已解析的 digest 不受影响）。

**"提为 baseline"如何不破坏不可变性（`PATCH /api/assets/{assetId}/baseline`）：**
- 不重打包、不改任何版本 tag 内容，只把 `baseline` 这个 floating tag 的指针从旧 digest 移到胜出版本的 digest。
- 中台同步更新 `asset_version.channel`：胜出版本 channel→baseline，旧 baseline→latest。
- 已在跑的客户端持有的是旧 digest 的完整 ref，不受影响；新会话 resolve 时才拿到新 baseline。这保证了灰度切换的平滑性与可回滚性（回滚 = 把指针移回旧 digest）。

**channel 取值**：`baseline`（默认稳定版）、`latest`（最新发布）、`experiment`/`canary`（灰度中）。与 `asset_version.channel` 字段（0/1/2）一一对应。

## 5. 评审结论

### 5.1 CEO 评审要点（产品价值 / 范围 / 盲点）

- **价值成立**：闭环的独特价值在"灰度 + 遥测 + 自进化"三者串起来——同类开源 coding agent 都缺"哪个 prompt/skill 版本更好"的量化回路，这是差异点。
- **范围克制得当**：团队自用 + 半自动 + 薄封装三个决策把 MVP 收敛到"能证明闭环"的最小集，没有过早做多租户/品牌化。✅
- **盲点提醒**：① 自进化的**价值密度**未验证——Hermes 生成的候选如果多数被驳回，审核会变负担，需在 MVP 观察"候选通过率"这个指标。② 灰度实验要有**足够样本**才有统计意义，10-100 人团队的流量可能让实验周期很长，需管理预期（这是团队级平台的固有约束，非架构缺陷）。

### 5.2 Eng 评审要点（可行性 / 架构 / 风险）

- **可行性高**：所有开源件均确认自托管 + 多 LLM，Python 单语言让 SDK 直连，胶水面小且清晰（两条缝）。✅
- **架构合理**：中台只存"薄映射状态"、内容交给 KitOps、统计交给 Langfuse、分流交给 GrowthBook，职责不重叠，符合最小胶水。✅
- **技术风险**：① **MCP Registry 处 preview**（v0.1，可能破坏性变更）——MVP 可先不强依赖它，工具分发用 KitOps ModelKit 直接带，MCP Registry 作为 L2 后续增强。② **KitOps 原生 agent/MCP 支持是 v1.12.0 新增**，较新，需锁版本验证。③ 客户端**容器运行时依赖**是部署硬约束，需在部署文档明确。

## 6. 部署形态与安全边界

### 6.1 部署形态

```
团队服务器（内网/私有云，一套 docker-compose）
├── agentmesh-api (FastAPI + SQLite/MySQL)      ← 中台
├── React 运营后台 (静态托管)
├── GrowthBook (self-hosted, MIT)               ← L3
├── Langfuse (self-hosted, MIT)                 ← L4
├── OCI Registry (Harbor/Zot, ClawHub 存储)     ← L2 资产
├── MCP Registry (可选, Go+PG)                   ← L2 工具（后续）
└── hermes-worker (定时 job)                     ← 自进化

开发者本机（macOS/Linux/WSL）
├── VS Code + 智能体模式                        ← 执行器（零装机、无需 Docker）
├── .github/hooks/agentmesh.json                ← 工作区级 hook 注册
├── agentmesh-hooks scripts (Python)            ← 两个脚本，随仓库分发
└── kit CLI                                     ← KitOps 客户端，用于 unpack ModelKit
```

- 平台自身服务全套私有化，核心服务不依赖第三方 SaaS（NFR2）✅。GrowthBook、Langfuse 均可自托管。**推理经 VS Code LM Provider 出境**（能否强制走中台 LiteLLM Proxy 见 §8 未决项）。

### 6.2 安全与数据隐私边界（NFR1 修正版）

| 数据 | 位置 | 是否出境 | 说明 |
|---|---|---|---|
| 原始用户输入 / 机密业务数据 | 经中台 Proxy → 云端厂商 | **是** | 用商业模型的必然；仅按所选厂商 API 出境，出境目标可在 Proxy 侧配置/审计 |
| LLM API key | 中台 LiteLLM Proxy | 集中托管 | **不下发客户端**；客户端只持内部 token 走 Proxy |
| 遥测 trace | 团队 Langfuse（自托管） | **否** | 含 variant/成功率等，**不含原始对话** |
| skill 沉淀 | 本机 | **默认否** | FR4 默认本地；FR6 显式授权才去标识化上传 |
| 资产（prompt/skill/tool） | ClawHub | 内网 | 团队共享资产，非用户私密数据 |

- **回流去标识化**：FR6 上传前剥离原始对话，只留 skill 文本。上传默认关闭，需显式授权（VS Code 设置 `agentmesh.uploadTranscript=true`）。
- **安全提醒（架构级）**：agentmesh-api、GrowthBook、Langfuse 等**内网服务默认无强认证**——团队自用可先用内网隔离 + 反向代理加 Basic Auth/SSO，但这属于**必须在部署阶段补齐的访问控制**，不能裸暴露。VS Code 智能体侧的工具审批与 `PreToolUse` hook 承担了原 OpenHands Docker 沙箱的安全职责，**不可禁用官方审批**。

## 7. 里程碑规划

| 里程碑 | 内容 | 验证目标 |
|---|---|---|
| **M0 环境就绪** | docker-compose 起 GrowthBook + OCI Registry + LiteLLM Proxy（Langfuse 复用现有实例）；本机 VS Code 智能体模式可用 + spike 验证能否走 Proxy | 各开源件自托管可用、VS Code 智能体推理通 |
| **M1 MVP 竖切（核心）** | GrowthBook + KitOps + Langfuse 一条竖切：VS Code `SessionStart` hook 取 variant→pull ModelKit→落盘 `.github/`→热加载→`Stop` hook 回灌 trace | **一次性验证 FR2+FR3+FR7 闭环成立**（最高优先级） |
| **M2 资产与后台** | agentmesh-api 资产/实验 CRUD + React 后台；版本命名约定落地 | 运营可建实验、管资产、看 variant 指标 |
| **M3 沉淀与自进化** | Letta 记忆接线 + 本地 skill 沉淀 + hermes-worker 产候选 + 审核发版 | FR4+FR5 半自动闭环，候选可审可发 |
| **M4 回流与增强** | FR6 去标识化回流；MCP Registry 工具分发；弱网离线缓存打磨 | 共享回流 + L2 工具层增强 |

> **M1 是风险最集中的一刀**：它同时验证灰度、资产版本、遥测三层的接线，建议最先打通，用最小代价证明整个架构成立。

## 8. 未决项（待后续澄清）

- ~~**版本命名约定细节**~~：**已定稿，见 §4.8**（channel 编进 tag 的 floating tag 指针方案）。✅
- ~~**OpenHands 加载外部 ModelKit 的官方机制**~~：**已消解**——客户端 pivot 到 VS Code 智能体模式后，加载点就是 `.github/agents/`、`.github/skills/`、`.github/instructions/`、`.mcp/config.json`，VS Code 官方热加载，无须自建加载点。见 [vscode-pivot 补丁](./2026-07-20-agentmesh-vscode-pivot.md) §6。✅
- **VS Code 智能体 LM base URL 覆盖机制（M0 前置 spike）**：能否强制走中台 LiteLLM Proxy 集中托管密钥+审计。若不支持，Proxy 降级为"只做审计与限流的旁路"，密钥托管由 VS Code Copilot Enterprise 或用户自配 provider 承担。
- **实验样本量与统计功效**：团队级低流量下实验周期评估，属运营策略，非架构项。已在遥测页做样本量进度提示（PRD-10）管理预期。
