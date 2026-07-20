# AgentMesh 产品需求文档（PRD）

> 依据：架构设计 [2026-07-20-agentmesh-architecture-design.md](./2026-07-20-agentmesh-architecture-design.md)、选型调研 [../research/2026-07-20-local-first-agent-platform-oss-stack.md](../research/2026-07-20-local-first-agent-platform-oss-stack.md)、视觉规范 [../../DESIGN.md](../../DESIGN.md)。
> 定位：团队自用（10-100 人）、本地优先、私有化、半自动自进化的 Agent 平台。
> 本文把闭环拆成可排期的需求 backlog，含优先级与验收标准。
>
> **⚠ 2026-07-20 客户端 Pivot**：角色①的触点从「OpenClaw 客户端」调整为「**VS Code 智能体模式 + Hooks**」，见补丁文档 [2026-07-20-agentmesh-vscode-pivot.md](./2026-07-20-agentmesh-vscode-pivot.md)。

## 1. 产品目标与北极星

**北极星**：让小团队把"用 Agent 干活"变成一个能自我度量、自我进化的闭环——每个 prompt/skill/tool 版本好不好有数据说话，好的版本能自动沉淀、灰度、发布。推理接入各主流云端厂商（Claude/OpenAI/Kimi 等），密钥与成本由中台统一托管。

**独特价值**：灰度（哪个版本在用）+ 遥测（哪个版本更好）+ 自进化（把更好的沉淀成新版本）三者串成回路。同类开源 coding agent 普遍缺这条量化回路。

**成败判据**：资产版本的迭代能否形成正向飞轮。可量化为两个核心健康指标：
- **候选通过率**（Hermes 产候选被审核通过的比例）——过低说明自进化在制造审核负担。
- **版本迭代收益**（新 baseline vs 旧 baseline 的成功率/反馈提升）——衡量飞轮是否正向。

## 2. 用户角色

| 编号 | 角色 | 核心诉求 | 主要触点 |
|---|---|---|---|
| ① | 终端使用者（开发者/运营/排障） | 开箱即用、免配密钥、可选不同厂商模型、越用越顺手 | **VS Code 智能体模式**（Agents / Skills / Instructions / Hooks / MCP 面板） |
| ② | 资产运营者（平台管理员） | 管版本、开灰度实验、看哪个版本好、审批发版 | React 运营后台 |
| ③ | 技能审核者（reviewer） | 高效判断候选质量、可追溯、批量处理 | 后台候选审核页 |
| ④ | 平台部署/运维者 | 私有化部署、访问控制、服务健康 | 部署脚本 + 系统设置 |
| ⑤ | 自进化系统（Hermes，非人） | 读轨迹→产候选→提交待审 | 后台 API |

> ②③ 在小团队常为同一人，但产品上区分：审核是决策动作、运营是管理动作，权限与视图不同。

## 3. 闭环链路（6 环 + 度量层）

```
   ⑥ 回流共享 ──► ① 会话启动（灰度绑定+拉资产）
        ▲                    │
        │                    ▼
   ⑤ 审核发版 ◄─ ④ 自进化 ◄─ ③ 技能沉淀 ◄─ ② 本地执行（推理+埋点）
   （后台审批）  （Hermes产候选）（Letta记忆）
        └──────── 度量层（Langfuse 按 variant 聚合）贯穿全环 ────────┘
```

闭环成立的关键在两条数据流动：**②的反馈燃料能否采到**、**⑤→①的发版能否自动接回灰度池**。
## 4. 需求 backlog（按优先级分层）

优先级定义：**P0** = 闭环骨架，不做则闭环不成立；**P1** = 让飞轮转起来（决定闭环是否正向）；**P2** = 规模化与治理（MVP 后）。
里程碑 M0-M4 对齐架构设计 §7。

### 4.1 第一层 · 闭环骨架（P0）

| ID | 需求 | 角色 | 环节 | FR | 里程碑 | 验收标准 |
|---|---|---|---|---|---|---|
| PRD-01 | 会话启动灰度绑定：VS Code `SessionStart` hook → client_id → `/api/hooks/resolve` → KitOps ref → `kit unpack` 落盘 `.github/` → 热加载 | ① | ① | FR2/FR3 | M1 | 同一 client_id 多次启动稳定绑定同 variant；命中缓存跳过拉取；无缓存回退 baseline；VS Code 面板即时显示新资产 |
| PRD-02 | trace 带 variant 标签回灌 Langfuse（`Stop` hook + `/api/sessions/ingest`） | ①/⑤ | ② | FR7 | M1 | 每条 trace 含 variant/asset 版本维度；Langfuse 可按 variant 过滤 |
| PRD-03 | 资产与版本管理后台（列表/详情/版本通道） | ② | 度量 | FR3 | M2 | 可查资产的全部版本、baseline/latest/experiment 通道、KitOps ref |
| PRD-04 | 灰度实验管理（CRUD + 状态流转 + 流量分配） | ② | 度量 | FR3 | M2 | 可建实验、绑 variant→版本、流量合计校验=100%、active/paused/archived 切换 |
| PRD-05 | skill 候选审核发版（列表/并排 diff/通过/驳回） | ③ | ⑤ | FR5/FR7 | M3 | 通过→触发 kit pack+push 新版本→建实验进灰度池；驳回带原因；已发布版本不可删 |
| PRD-06 | 遥测按 variant 聚合展示（成功率/时延/反馈） | ② | 度量 | FR7 | M1/M2 | 后台按 variant 展示成功率、P50 时延、正反馈率 |

### 4.2 第二层 · 让飞轮转起来（P1）

| ID | 需求 | 角色 | 环节 | FR | 里程碑 | 验收标准 |
|---|---|---|---|---|---|---|
| PRD-07 | 用户反馈入口（👍/👎 + 可选原因） | ① | ② | 新增 | M3 | 每次会话结束/关键动作后可反馈；反馈随 trace 打 variant 标签入 Langfuse |
| PRD-08 | 候选通过率 / 审核积压监控 | ②/③ | ④/⑤ | 新增 | M3 | 后台展示近 N 日候选通过率趋势；积压候选数超阈值提醒 |
| PRD-09 | 实验结论判定 + 胜出 variant 一键提 baseline | ② | 度量→① | 新增 | M3 | 达样本量后标记胜出 variant；一键将其 channel 提为 baseline，闭环接回① |
| PRD-10 | 样本量 / 统计功效提示 | ② | 度量 | 新增 | M3 | 实验详情显示当前样本量与达到统计显著所需样本量的进度 |
| PRD-11 | 技能沉淀可视化：`.github/skills/` 下的 SKILL.md 即 VS Code Skills 面板；沉淀 skill 走 VS Code 内置 Skills 视图 | ① | ③ | FR4 | M3 | VS Code Skills 面板显示已沉淀 skill；用户可通过 `Chat: Generate Skill` 或手动创建"值得沉淀"的 SKILL.md |
| PRD-12 | 候选自带元信息（预期改进点 + 来源轨迹链接） | ⑤/③ | ④ | FR5 | M3 | 候选详情含 Hermes 预期改进说明 + 可跳转来源 Langfuse/Letta 轨迹 |

### 4.3 第三层 · 规模化与治理（P2，MVP 后）

| ID | 需求 | 角色 | 环节 | FR | 里程碑 | 验收标准 |
|---|---|---|---|---|---|---|
| PRD-13 | 回流共享 + 去标识化预览：VS Code 设置 `agentmesh.uploadTranscript=true` 显式开启；`Stop` hook 剥离原文，仅上传去标识化 skill | ②/① | ⑥ | FR6 | M4 | 上传默认关闭；显式授权；上传前预览去标识化内容确认不含机密 |
| PRD-14 | MCP Registry 工具层分发 | ② | ①/② | FR2 | M4 | 工具目录可浏览；ModelKit 可引用 MCP server |
| PRD-15 | 访问控制 / SSO（部署阶段必补） | ④ | 全 | NFR | M2+ | 内网服务加 Basic Auth/SSO；后台按角色区分权限；不裸暴露 |
| PRD-16 | 资产缓存与更新策略 | ① | ① | NFR | M4 | 命中本地缓存跳过重复拉取；缓存过期与更新策略明确（注：纯云端推理，不再承诺离线可用） |
| PRD-17 | 审核历史 / 审计线 | ③/④ | ⑤ | 新增 | M4 | 记录谁在何时通过/驳回/暂停/发版；可追溯 |

## 5. 非功能需求（对齐架构 §2.2）

| NFR | 要求 | 验收 |
|---|---|---|
| NFR1 | 平台自身数据私有自托管；推理密钥集中托管 | 资产/实验/遥测/审核数据不进第三方 SaaS；LLM 密钥仅在中台 LiteLLM Proxy，不下发客户端；trace 不含原始对话。推理内容按厂商 API 出境（用商业模型的必然，接受） |
| NFR2 | 可私有化部署 | 一套 docker-compose 起平台服务；平台自身不依赖第三方 SaaS（推理除外） |
| NFR3 | 最小胶水 | 胶水集中在两条缝（L3→L2、L2→L1）；其余复用开源件 |
| NFR4 | 许可证避免 GPL | 全 MIT/Apache-2.0/BSD；已排除 Unleash(AGPL) |
| NFR5 | 可扩展 1000+ | SQLite→MySQL 平滑迁移；中台只存薄映射状态 |
| ~~NFR6~~ | ~~本地弱网可用~~ | **已废止**：纯云端推理，断网不可用；资产缓存仅避免重复拉取，不再作离线可用承诺 |

## 6. 排除项（本期不做）

多租户/组织隔离、品牌可配置/一键交付、全自动 skill 改写、L1 自建执行器抽象、Unleash（许可证）。

## 7. 风险与盲点

| 风险 | 来源 | 缓解 |
|---|---|---|
| 自进化价值密度未验证（候选多被驳回则审核变负担） | CEO 评审① | MVP 监控候选通过率（PRD-08） |
| 小团队低流量导致实验周期长 | CEO 评审② | 样本量提示管理预期（PRD-10）；属运营约束非架构缺陷 |
| MCP Registry 处 preview 可能破坏性变更 | Eng 评审① | MVP 不强依赖，工具用 KitOps 直接带 |
| 内网服务默认无强认证 | 架构 §6.2 | 部署阶段必补访问控制（PRD-15），不可裸暴露 |
| VS Code 智能体 LM base URL 覆盖未定 | Pivot 补丁 §11 | M0 前置 spike；不通则中台 Proxy 降级为旁路 |
| VS Code Hooks 处 preview 期字段变更 | Pivot 补丁 §11 | 只用稳定字段（session_id/cwd/transcript_path/tool_name/tool_input），避开实验字段 |

## 8. 里程碑与需求映射

| 里程碑 | 目标 | 覆盖需求 |
|---|---|---|
| M0 环境就绪 | 平台开源件自托管可用、VS Code 智能体 LM 出境路径确认（Proxy 走通或降级）、Hooks 加载点验证 | 基础设施 + Pivot 前置 spike |
| M1 MVP 竖切 | 验证 FR2+FR3+FR7 闭环成立（`agentmesh-hooks` 两个脚本 + 中台 resolve/ingest 接口） | PRD-01/02/06 |
| M2 资产与后台 | 运营可建实验、管资产、看指标 | PRD-03/04/06/15 |
| M3 沉淀与自进化 | 半自动闭环，候选可审可发，飞轮转起来 | PRD-05/07/08/09/10/11/12 |
| M4 回流与增强 | 共享回流 + L2 工具层 + 治理 | PRD-13/14/16/17 |

