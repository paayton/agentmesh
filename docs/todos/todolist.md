# 待办清单

> 由 EE 工作流各指令自动收集 + 手动添加。查看：/ee-todo
> 需求来源：[PRD](../plans/2026-07-20-agentmesh-prd.md) · [架构设计](../plans/2026-07-20-agentmesh-architecture-design.md) · [角色矩阵](../plans/2026-07-20-agentmesh-role-touchpoint-matrix.md) · [VS Code Pivot 补丁](../plans/2026-07-20-agentmesh-vscode-pivot.md)

## 进行中里程碑：M0 环境就绪 → M1 MVP 竖切

### M0 环境就绪（P0 · 阻塞 M1，先行）

- [~] `[P0]` `[M0]` docker-compose 起 GrowthBook + Zot Registry + LiteLLM Proxy;Langfuse 复用团队现有实例 —— **骨架就绪(deploy/),待团队服务器实跑** <!--todo:20260720-002-->
- [ ] `[P0]` `[M0]` **spike：VS Code 智能体 LM base URL 覆盖机制**——能否强制走中台 LiteLLM Proxy;不通则 Proxy 降级为旁路（Pivot 补丁 §8/§11 未决项）<!--todo:20260720-003-->
- [x] ~~`[P0]` `[M0]` 实测确认 OpenHands 加载外部 ModelKit 的机制~~ —— **已消解**：客户端 pivot 到 VS Code 后，加载点是 `.github/agents/`、`.github/skills/`、`.github/instructions/`、`.mcp/config.json`，VS Code 官方热加载 <!--todo:20260720-004-->
- [ ] `[P0]` `[M0]` **验证 VS Code Hooks 落地**：本机装 hook 配置（`.github/hooks/agentmesh.json`）+ 官方 `Developer: Show Agent Debug Logs` 看事件触发 <!--todo:20260720-018-->

### M1 MVP 竖切（P0 · 核心，一次性验证 FR2+FR3+FR7 闭环）

- [ ] `[P0]` `[M1]` KitOps 打一个样例 ModelKit(coding-agent, layout 含 agents/skills/instructions/hooks/mcp,见 Pivot 补丁 §6)并 push 到 registry,按 §4.8 命名约定打 tag <!--todo:20260720-005-->
- [ ] `[P0]` `[M1]` GrowthBook 建一个多值 flag 实验,variant 值 = 版本串,验证 client_id 粘性分桶 <!--todo:20260720-006-->
- [ ] `[P0]` `[M1]` agentmesh-api 实现 `/api/hooks/resolve`（批量）+ `/api/sessions/ingest`（Stop hook 回灌）+ `/api/assets/resolve`（单资产兜底） <!--todo:20260720-007-->
- [ ] `[P0]` `[M1]` **agentmesh-hooks**：`session_start.py`（调 resolve + kit unpack 落盘 `.github/`）+ `stop.py`（读 transcript + POST ingest）——替换原 openclaw-agent <!--todo:20260720-008-->
- [ ] `[P0]` `[M1]` trace 带 variant 标签回灌 Langfuse,后台可按 variant 过滤(PRD-02) <!--todo:20260720-009-->
- [ ] `[P0]` `[M1]` 竖切联调：跑通「SessionStart→resolve→pull→落盘→VS Code 热加载→执行→Stop→ingest→trace 回灌」全链路 <!--todo:20260720-010-->

## 待排期（M2+，backlog 见 PRD §4）

- [ ] `[P0]` `[M2]` agentmesh-api 资产/实验 CRUD + React 后台落地(原型已就绪)(PRD-03/04/06) <!--todo:20260720-011-->
- [ ] `[P1]` `[M2]` 新接口 `PATCH /api/assets/{assetId}/baseline` 提 baseline(§4.8,原型已演示)(PRD-09) <!--todo:20260720-012-->
- [ ] `[P0]` `[M3]` Letta 记忆接线 + 本地 skill 沉淀 + hermes-worker 产候选 + 审核发版(PRD-05/11/12) <!--todo:20260720-013-->
- [ ] `[P1]` `[M3]` 客户端 👍/👎 反馈入口 + `/api/feedback` 回灌(PRD-07,自进化燃料) <!--todo:20260720-014-->
- [ ] `[P1]` `[M3]` `/api/metrics/candidates/pass-rate` 候选通过率/积压监控(PRD-08) <!--todo:20260720-015-->
- [ ] `[P2]` `[M4]` FR6 去标识化回流 + MCP Registry 工具分发 + 弱网缓存打磨(PRD-13/14/16) <!--todo:20260720-016-->
- [ ] `[P2]` `[M2+]` 访问控制/SSO(部署阶段必补,内网服务不可裸暴露)(PRD-15) <!--todo:20260720-017-->

## 已完成

- [x] `[ee-research]` 开源选型调研(L1-L5 分层选型) <!--todo:done-research-->
- [x] `[ee-design]` 整体架构设计(四层映射 + 数据流 + DDL + 接口 + §4.8 版本约定定稿) <!--todo:done-arch-->
- [x] `[ee-design]` PRD(17 条需求 backlog,三层优先级) <!--todo:done-prd-->
- [x] `[ee-design]` 角色-触点矩阵(5 角色 × 6 环节) <!--todo:done-matrix-->
- [x] `[ee-design]` 闭环全景图原型 + 运营后台原型(4 页 + P1 增强) <!--todo:done-proto-->
