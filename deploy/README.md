# AgentMesh M0 部署骨架

对应 todolist `20260720-002`。起团队服务器一套自托管环境。

## 范围

| 服务 | 层 | 说明 |
|---|---|---|
| GrowthBook + MongoDB | L3 灰度 | UI :3000 / API :3100 |
| Zot | L2 OCI Registry | KitOps ModelKit 存储，:5000 |
| LiteLLM Proxy | L1 模型路由 | 云端多厂商统一路由（Claude/OpenAI/Kimi），集中管密钥，:4000 |
| Langfuse | L4 遥测 | **复用团队现有实例**，通过 `.env` 接入，不在此起栈 |
| agentmesh-api / hermes-worker | 中台/自进化 | 占位，M1/M3 代码就绪后启用 |

## 快速开始

```bash
cp .env.example .env
# 编辑 .env：至少改 GB_JWT_SECRET / GB_MONGO_PASS，填入 LANGFUSE_* 现有实例信息
docker compose up -d
docker compose ps          # 看健康状态
```

- GrowthBook: http://localhost:3000 （首次进入建管理员账号，建实验）
- Zot registry: http://localhost:5000/v2/_catalog （验证 registry 活着）
- LiteLLM Proxy: `curl http://localhost:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY"` （验证厂商路由）

## 安全提醒（架构 §6.2）

内网服务默认无强认证。团队自用先用**内网隔离 + 反向代理加 Basic Auth/SSO**，不可裸暴露公网。`GB_JWT_SECRET` / `GB_MONGO_PASS` / `LITELLM_MASTER_KEY` 必须改为强随机值。**厂商 API key 仅存于 LiteLLM Proxy 容器，不下发客户端。** `.env` 不入库。

## 里程碑

M0 其余两项在本机（非 compose）：
- `20260720-003` OpenHands 经中台 LiteLLM Proxy 调通云端厂商（Claude/OpenAI/Kimi）
- `20260720-004` OpenHands 加载 ModelKit 机制实测（M1 落地前置，调研进行中）
