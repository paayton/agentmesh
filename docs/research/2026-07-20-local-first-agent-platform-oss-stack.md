# 本地优先 / 资产云端分发 / 可自进化 / 灰度实验 私有化 Agent 平台 —— 开源方案选型调研

> ⚠️ **方向修正（2026-07-20 晚，晚于本调研）**：产品决策改为**纯云端多厂商推理**——推理接入 Claude/OpenAI/Kimi 等商业厂商，由中台自托管 **LiteLLM Proxy** 统一路由、集中管密钥。**不再使用本地推理（Ollama/vLLM）**，数据边界从"数据不出本地"调整为"平台自身数据私有自托管、推理内容按厂商 API 出境"。本文正文保留为当时调研快照（其中本地推理/气隙/离线相关结论已不适用）；最新口径以 [架构设计 §2.2/§6.2](../plans/2026-07-20-agentmesh-architecture-design.md) 与 [PRD NFR1](../plans/2026-07-20-agentmesh-prd.md) 为准。LiteLLM 作为统一路由层的选型本身不变，只是后端从本地换成云端厂商。

> 调研日期：2026-07-20　信息来源：24 个（抓取）　核验声明：25 条（对抗验证通过 23 条，否定 2 条）
> 约束回顾：偏 coding assistant 但覆盖运营/系统排障/日常业务操作等泛工程场景；排除 Claude Code 生态；需多 LLM（Ollama/vLLM/LiteLLM）；私有化自托管；许可证首选 MIT/Apache-2.0、避免 GPL 传染；最小胶水代码、接受多开源项目拼装。

---

## 执行摘要

在你给定的约束下，几乎可以用一套**全 MIT/Apache-2.0 的分层拼装**跑通闭环，胶水代码集中在"资产版本 → 执行器加载"这一条缝上。分层结论：

- **执行层（L1）**：`Aider`（Apache-2.0，交互式结对）+ `OpenHands`（MIT 核心，底层 LiteLLM 接 100+ 模型含 Ollama/vLLM，Docker 沙箱，有 headless/CI 模式）两个锚点，正好覆盖"交互 coding"与"自主跑运营/排障任务"两端。
- **资产分发 / 版本基线（L2）**：`KitOps`（Apache-2.0，用 OCI ModelKit 把 prompt/skill/MCP 配置/模型打成一个带 SHA-256 不可变摘要的版本化包，支持按需选择性拉取）是版本锁定基线的最佳匹配；辅以 `MCP Registry`（自托管工具目录）、`MCPJungle`（MPL-2.0 网关）、`Dify DSL`（YAML 应用打包 + 导入期版本兼容校验）。
- **灰度实验（L3）**：`GrowthBook`（MIT，自托管免费，开源版即含 flag + 实验 + 分析）是首选；`Flagsmith`（核心 BSD-3-Clause，RBAC/SSO 属闭源企业版）为备选；**`Unleash` 已排除**——官方确认自 v8.0.0 起主源码由 Apache-2.0 转 **AGPLv3**，直接踩"避免 GPL 传染"红线。
- **遥测可观测（L4）**：`Langfuse`（MIT 核心，可完全离线/气隙部署，原生 LangChain/LiteLLM/OpenTelemetry）是许可证首选；`Arize Phoenix` 可免费自托管但为 Elastic License 2.0（source-available，非 MIT/Apache，但也非 GPL）。
- **技能沉淀 / 自进化（L5）**：`Letta`（原 MemGPT，Apache-2.0，模型无关含 Ollama/vLLM，本地 CLI，自改进记忆）是核心，出自一份"9 个开源自改进 Agent 框架"的清单。

一句话推荐组合：**Aider + OpenHands（L1）｜KitOps + MCP Registry（L2）｜GrowthBook（L3）｜Langfuse（L4）｜Letta（L5）**。

> L3 真正的难点不在选型，而在接缝：这些工具是为"代码功能开关"设计的（flag→布尔→走哪个分支），而你要的是"按流量把用户绑定到不同 **asset 版本**"（FR3）。GrowthBook/Flagsmith 的**多值 flag + 百分比 rollout + 粘性分桶**能返回一个"版本字符串"，客户端再据此去 L2 拉对应版本包——链路可通，但"flag 返回版本号 → 加载 KitOps/Dify 版本"这段是**你要写的胶水**。详见下文《L3 接线设计》。

---

## 分层候选对比矩阵

> 说明：✅=已核验确认，⚠️=有许可证/成熟度注意项，❓=本轮未充分验证。许可证以核验结论为准（部分推翻了旧资料）。

### L1 · Agent 执行框架

| 候选 | 许可证 | 自托管 | 本地/多 LLM | 成熟度 | 小团队可维护 | 定位 |
|---|---|---|---|---|---|---|
| **OpenHands** | MIT（核心）✅ | ✅ | ✅ LiteLLM 100+ 提供商，含 Ollama/llama.cpp/vLLM/MLX | ~75-76k stars | 单服务 + Docker 沙箱，中 | 自主/沙箱执行、headless CI，跑运营/排障 |
| **Aider** | Apache-2.0 ✅ | ✅ | ✅ 本地 Ollama，无需 key、代码不出机 | ~6.8M PyPI 装机（项目自报） | 极轻，CLI | 交互式结对编程（**非自主**） |
| Goose / Cline / Continue / Roo Code / Kilo Code | 多为 Apache-2.0 | ✅ | 多支持 Ollama/多模型 | 中-高 | 轻 | 备选 coding agent |
| （Zed 核心） | GPL/AGPL ⚠️ | — | — | — | — | 因 GPL 传染排除 |

要点：Aider 是"结对程序员"不是自主任务执行器；OpenHands 才是自主端。二者互补，恰好覆盖你"偏 coding 但要泛工程"的双重诉求。LiteLLM 是贯穿全栈的统一模型路由缝。

### L2 · 资产分发与版本基线

| 候选 | 许可证 | 自托管 | 打包对象 | 版本能力 | 注意项 |
|---|---|---|---|---|---|
| **KitOps** | Apache-2.0 ✅（CNCF） | ✅ 任意 OCI registry | 模型/数据集/prompt/skill 文件/MCP 配置/代码 → 单个版本化 OCI ModelKit | SHA-256 不可变摘要、锁定"prompt+模型+skill"整体、`kit unpack --filter=prompts` 选择性拉取、`--as-skill` 装 SKILL.md | v1.12.0 才加原生 agent/MCP 支持（较新） |
| **MCP Registry**（官方） | MIT→Apache-2.0 过渡 ✅ | ✅ Go + PostgreSQL，Docker Compose | MCP servers/tools 目录（"MCP 应用商店"） | 组织可建子 registry | ⚠️ preview（v0.1，可能破坏性变更）；只分发 MCP server，不含 prompt/skill/workflow；需自备持久 Postgres |
| **MCPJungle** | MPL-2.0 ⚠️（弱文件级 copyleft，非 GPL） | ✅ | 统一网关，聚合多 MCP server 的 tools/prompts/resources | 单端点集中发现 | 访问控制/OpenTelemetry 需企业版 |
| **Dify DSL** | —（应用层打包能力） | ✅ | YAML 打包完整应用：workflow 编排/节点/模型参数/prompt 模板/KB 连接（不含数据、不含 secret） | 导入期版本兼容校验，旧版会告警 | 与 KitOps 的 OCI 路线互补（偏 workflow 应用级） |

要点：**KitOps 直接命中你"自建 OCI/registry 打包 prompt/skill/tool/workflow"的诉求**，是版本基线的一等公民。MCP Registry 负责工具发现，Dify DSL 负责应用级打包，三者分工不冲突。

### L3 · A/B 灰度实验开关（已补轮核实，2026-07-20）

| 候选 | 许可证 | 自托管 | 开源版能力 | 企业墙 | 结论 |
|---|---|---|---|---|---|
| **GrowthBook** | MIT ✅ | ✅ Docker/K8s | flag + 实验 + 产品分析全含；统计引擎齐全（贝叶斯/频率/CUPED/sequential/bandit/SRM） | 少 | **首选**，许可证零障碍 |
| **Flagsmith** | 核心 BSD-3-Clause ✅ | ✅ | flag、remote config、user targeting、multivariate、targeting rules | ⚠️ RBAC、SAML/SSO、部分 DB 集成属**闭源企业版** | **备选**；小团队核心够用，要 SSO/细粒度权限需付费 |
| ~~Unleash~~ | ❌ **AGPL-3.0**（v8.0.0 起主源码 + `unleash-server` npm 由 Apache-2.0 转 AGPLv3；官方 Docker 镜像/Helm charts 仍 Apache-2.0） | ✅ | — | 高级实验/访问控制需付费 | **排除**：主源码 AGPL 网络 copyleft，直接踩"避免 GPL 传染"红线 |

要点：Unleash 的 AGPL 疑点已由官方公告落实为真（v8.0.0 起），出局。**GrowthBook（MIT）是许可证 + 能力双优的首选**，Flagsmith 核心 BSD-3 可用但有企业墙。真正的工程难点见下节。

### L4 · LLM 遥测与可观测

| 候选 | 许可证 | 自托管/离线 | 多 LLM 集成 | 注意 |
|---|---|---|---|---|
| **Langfuse** | MIT（核心全功能：tracing/评估/prompt 管理/实验/标注/playground，无用量上限）✅ | ✅ 笔记本→气隙集群，联网可选，自托管数据不出网 | ✅ 原生 LangChain/LangGraph、LiteLLM（SDK+Proxy）、OpenTelemetry（作 OTLP 后端） | 仅 SCIM/审计日志/数据保留/RBAC 等企业模块需 license key；2026-01 被 ClickHouse 收购，能力不变 |
| **Arize Phoenix** | Elastic License 2.0 ⚠️（source-available，非 MIT/Apache，但非 GPL） | ✅ 免费自托管、无功能墙、可气隙（单 Docker） | OTel 对齐 | ELv2 限制"作为托管服务对外提供"；部分子包（evals/otel）许可证不同 |
| OpenLLMetry / OpenInference / OpenLIT | Apache-2.0 ✅ | ✅ | OTel 对齐的 instrumentation 库 | 偏底层埋点，喂给厂商中立的 OTel collector |

要点：**Langfuse 是许可证 + 功能双优的首选**，且原生 LiteLLM 集成直接接你的多 LLM 需求。Phoenix 因 ELv2 退居备选。

### L5 · 技能沉淀与自进化

| 候选 | 许可证 | 自托管 | 本地/多 LLM | 自进化机制 | 注意 |
|---|---|---|---|---|---|
| **Letta**（原 MemGPT） | Apache-2.0 ✅（UC Berkeley 团队） | ✅ App Server/Docker | ✅ 模型无关，环境变量启用 OpenAI/Ollama/vLLM/LM Studio/LocalAI，可多提供商并存 | OS 式分层 RAM/disk 记忆，agent 用 tool call 决定换入换出，"随时间学习与自改进" | ~21k stars；⚠️"local 模式"指**状态存储在本地**，不代表推理在本地（默认仍调远程，除非指向 Ollama/vLLM） |
| （9 框架清单） | 多为开源 | — | — | HyperAgents、Letta、LangGraph、Agent0、AutoSkill、MemSkill、EvoAgentX 等 | 出自 Turing Post，仅标题/摘要核验 |

要点：Letta 是 L5 的核心承载。注意"本地"语义陷阱——记忆状态本地 ≠ 推理本地。

---

## 推荐组合方案（分层拼装）

```
L1 执行   Aider（交互结对） + OpenHands（自主/沙箱，LiteLLM 多模型）
L2 资产   KitOps（OCI 版本基线） + MCP Registry / MCPJungle（工具分发） + 可选 Dify DSL（workflow 打包）
L3 灰度   GrowthBook（MIT 首选） ｜ Flagsmith（BSD-3 核心，备选）　【Unleash 已排除：AGPL】
L4 遥测   Langfuse（MIT 首选） ｜ Phoenix（ELv2 备选）
L5 自进化 Letta（Apache-2.0，自改进记忆）
```

满足约束的核对：
- **许可证**：除 MCPJungle（MPL-2.0）与 Phoenix（ELv2）外几乎全 MIT/Apache-2.0/BSD-3，且均非 GPL、均可替换 → "避免 GPL 传染"满足。**注意 L3 必须避开 Unleash v8+（AGPL）**。
- **自托管**：全部可自托管。
- **多 LLM**：OpenHands / Langfuse / Letta 均确认支持 Ollama/vLLM/LiteLLM。
- **最小胶水**：每层一个自托管服务，LiteLLM 作为跨层统一模型路由缝，胶水集中在 L2→L1 的资产加载与 L3→L2 的版本选择（见下节）。

> 该组合置信度为**中偏高**：L1/L2/L4/L5 属跨发现项集成判断，L3 已单独核实到许可证与能力层面。

---

## L3 接线设计：灰度 flag ↔ 资产版本

这是整个闭环（FR3）真正的工程难点，也是唯一没有现成组件、需要自己写胶水的地方。核心错位在于：

- **flag 工具的原生模型**：`flag → 布尔/多值 → 代码里走哪个分支`（为"功能开关"设计）。
- **你要的模型**：`按流量把 client 稳定绑定到某个 asset 版本 → 客户端拉取并加载对应的 KitOps ModelKit / Dify 应用版本`。

桥接方式（GrowthBook 与 Flagsmith 都具备所需原语）：

1. **用多值 flag 承载版本号**。在 GrowthBook 建一个 experiment，variant 的值直接是资产版本字符串（如 `asset://coding-agent@1.4.2` / `@1.5.0-canary`），而非布尔。Flagsmith 用 multivariate flag / remote config 同理。
2. **用一致性哈希做粘性分桶**。GrowthBook/Flagsmith 均支持按 `client_id` 做百分比 rollout 且稳定分桶，天然满足 FR3 的"同一 client 多次请求绑定同一 variant"——这一层不用自己实现哈希。
3. **客户端胶水（要写的部分）**：启动/定时向 L3 SDK 传 `client_id` 取回版本字符串 → 交给 L2 拉取器 `kit unpack <ref>@<version>`（KitOps 的不可变 SHA-256 摘要保证同版本 = 同内容）→ 加载进 L1 执行器。这段大约就是"一次 flag 查询 + 一次 kit pull + 缓存/回退"的量级。
4. **实验闭环回 L4**：把 variant 值作为一个维度标签打进 Langfuse trace（成功率/时延/反馈按 variant 聚合），实验结论就能在 Langfuse 里直接看，无需再建统计后端。

需要自己补的最小胶水清单：
- 版本字符串 ↔ KitOps ref 的命名约定与解析；
- 客户端"取 flag → 拉版本 → 加载 → 失败回退到 baseline"的小状态机；
- variant 标签注入 Langfuse 的埋点。

> 结论：链路可通，无架构级障碍；GrowthBook 负责"谁用哪个版本 + 粘性分桶"，KitOps 负责"版本即不可变内容"，Langfuse 负责"哪个版本更好"。三者之间只差一层薄胶水。这是建议 MVP 最先打通的一条竖切。

---

## 争议与被否定信息（对抗验证 0-3 淘汰）

1. **"9 个自托管 coding agent 的许可证/接口/模型对比表"**（来自 ssojet 博客）— 被 3 票否定。具体的九项对比数值不可依赖。
2. **"OpenHands … CodeAct v3 配 Claude Opus 4.6 在 SWE-bench Verified 达 68.4%、70k+ stars、490+ 贡献者"**（同源博客）— 被 3 票否定。**具体 benchmark 分数与贡献者数字不可引用**（OpenHands 为 MIT、Docker 沙箱这两点由其他来源另行确认为真）。

---

## 开放问题

1. ~~L3 灰度层整体待验证~~ — **已解决**（2026-07-20 补轮）：Unleash v8+ 转 AGPL 出局，GrowthBook（MIT）首选、Flagsmith（BSD-3 核心）备选；"flag→资产版本"接线方式见《L3 接线设计》一节。剩余待落地项：版本命名约定与客户端回退状态机的具体实现。
2. **L2→L1 集成接缝**：OpenHands/Aider 是否有官方机制在启动时拉取"版本锁定的 skill/prompt 包"，还是必须写自定义胶水？（当前判断是需自定义胶水，量级见 L3 接线设计第 3 点。）
3. **全栈真·本地推理**：当唯一后端是自托管 Ollama/vLLM 且无外网时，OpenHands、Langfuse（playground/评估）、Letta 各自哪些功能会**静默依赖远程提供商**？
4. **技能可分发性**：9 个自改进框架中，哪些支持把"学到的技能"持久化为**可分发工件**（而非仅 agent 内部记忆），从而回流进 L2 的 KitOps/registry 分发环？

---

## 数据局限性

- **L3 已补轮核实（2026-07-20）**：首轮 Unleash/GrowthBook/Flagsmith 声明被预算裁掉（budgetDropped=6）未进验证集，已用定向 WebSearch 补齐至许可证/能力层面（来源见下）。仍未做端到端验证的是"flag→资产版本"接线的**具体实现**（属工程落地，非选型问题）。
- **许可证细节**：MCPJungle=MPL-2.0、Phoenix=ELv2，均非 MIT/Apache 首选但非 GPL；Unleash 许可证有 Apache/AGPL 冲突信息，务必以官方仓库 LICENSE 为准。
- **成熟度/时效**：MCP Registry 明确处 preview（v0.1 API 冻结，GA 前可能破坏性变更/数据重置），dev-compose 的 DB 是临时的（需自备持久 Postgres）；KitOps 原生 agent/MCP 支持是 v1.12.0 新增；全部来源为 2026 年，领域变动快。
- **"本地"语义**：Letta 的 local 模式指状态存储非推理位置；Aider 是结对而非自主。
- **来源质量**：L2/L4/L5 主要建立在厂商主文档与 GitHub LICENSE（强）；L1 部分依赖博客（ssojet/pinggy，已交叉印证）；七层框架与"9 框架"计数为二级来源（O'Reilly、Turing Post），后者仅凭标题/摘要核验。Aider 6.8M 装机为项目自报。

---

## 参考来源

**Primary（主文档 / 官方仓库）**
- KitOps — https://kitops.org/docs/overview/ ；Kitfile 格式 https://kitops.org/docs/kitfile/format ；https://github.com/kitops-ml/kitops
- MCP Registry — https://github.com/modelcontextprotocol/registry ；https://blog.modelcontextprotocol.io
- MCPJungle — https://github.com/duaraghav8/MCPJungle
- Dify — https://enterprise-docs.dify.ai/en/3.10.x/use/workspace/app-management ；https://docs.dify.ai
- Langfuse — https://langfuse.com/handbook/chapters/open-source ；/self-hosting/networking ；/integrations/gateways/litellm
- LiteLLM×Langfuse — https://docs.litellm.ai/docs/observability/langfuse_integration
- Arize Phoenix — https://arize.com/docs/phoenix/self-hosting/license ；/self-hosting
- Letta — https://pypi.org/project/letta/ ；https://github.com/letta-ai/letta ；https://docs.letta.com/letta-code/cli/
- OpenHands 文档 — https://docs.openhands.dev

**Secondary（二级分析）**
- O'Reilly Radar《The Open Source Agent Toolkit in 2026》— https://www.oreilly.com/radar/the-open-source-agent-toolkit-in-2026/
- Turing Post《Agent self-improvement》— https://www.turingpost.com/p/agentselfimprovement

**L3 补轮核实来源（2026-07-20，定向核验）**
- Unleash 转 AGPLv3 官方公告 — https://www.getunleash.io/blog/unleash-moving-to-agplv3
- Unleash 版本与许可证说明（v8.0.0 起 AGPLv3） — https://docs.getunleash.io/support/availability
- GrowthBook 开源发布 — https://www.growthbook.io/blog/announcing-growth-book-open-source-release ；实验能力 https://www.growthbook.io/products/experimentation ；MIT https://pypi.org/project/growthbook/
- Flagsmith 开源说明 — https://www.flagsmith.com/open-source ；开源/自托管 FAQ（核心 BSD-3、EE 闭源） https://docs.flagsmith.com/support/faq/open-source-self-hosted

**Blog（博客，已交叉印证或仅参考）**
- ssojet / pinggy.io / opensourcealternatives.to / fast.io（L1）
- thomasvitale.com / stacklok.com（L2）
- featbit.co / codenote.net / getunleash.io / growthbook.io（L3）
- latitude.so / futureagi.com（L4）
- vectorize.io / fountaincity.tech（L5）

---
*本报告由 ee-deep-research 生成，使用 deep-research 多源对抗验证框架*
*检索角度: 5 个　抓取来源: 24 个　提取声明: 111 条　核验: 25 条（通过 23 / 否定 2）　agent 调用: 106**
*L3 层于 2026-07-20 定向补轮核实（Unleash/GrowthBook/Flagsmith 许可证与能力）*
