# UserTrail Memory v0.69

对话历史包、HTTP 接入和场景测试的开发步骤见[开发笔记](scenarios/DEVELOPER_NOTES.md)。

UserTrail Memory（gioruno）是面向对话历史的记忆检索系统：持久化原始消息，从同一用户的完整历史中寻找相关证据，向外部回答模型提供带说话者、会话和可用日期的原文上下文。

**参赛成员：郑俊烽｜机构：北京理工大学｜导师：秦宏超**

**Agent Memory Challenge 2026｜Textual Memory｜开源方法榜（academic）**

本系统提供 Add / Search 接口，不在记忆服务中生成最终答案。Answer、Judge 与评分由赛事平台统一完成。

## 参评版本与材料

| 项目 | 信息 |
| --- | --- |
| 系统版本 | v0.69，V3 source competition |
| 参评源码目录 | [`releases/v0.69-v3-current-source/`](releases/v0.69-v3-current-source) |
| 服务入口 | `m06_candidate:app`，从上述目录启动 |
| 固定源码提交 | [`e50bf64e067c7ad032538213110f6587d91620b9`](https://github.com/gioruno-banana/usertrail-memory/tree/e50bf64e067c7ad032538213110f6587d91620b9/releases/v0.69-v3-current-source) |
| 检索机制 SHA256 | `7c42aab6055539082b3a0650b83d15d58bb2749f9851e1d4713a80660fdd951d`（该目录 `history/usertrail/candidates.py`） |
| Embedding | `text-embedding-v4`，1024 维，batch size 10 |
| 检索配置 | `query_document_evidence`；证据文本预算 24,000 字符 |
| 正式任务参数 | Add 并发 16，Search 并发 16，`top_k=100` |
| 操作与配置 | [运行指南](scenarios/RUN_GUIDE.md) |
| 方法、接口与资源说明 | [参赛补充说明](SUBMISSION_v0.69.zh-CN.md) |
| 许可证 | [MIT License](LICENSE) |

本次文档补充不改变以上固定源码。仓库根目录的演示与 `studies/` 属于早期研究材料；复现参评服务请使用上表指定的目录和入口。

## 方法：让初始候选池之外的历史证据参与竞争

1. **原文写入。** 按 `user_id` 持久化消息与向量，保留 `session_id`、说话者、消息顺序和已有时间戳。不把 assistant 建议改写为用户偏好，不生成用户画像。
2. **完整历史来源检索。** 在常规检索之后，将同一用户已写入的全部来源纳入候选竞争，以来源内最相关的文本块代表该来源。语义相似度与词法相关度通过 RRF 融合，减少同一来源的多个块占满候选池的情况。
3. **按实际覆盖变化启用。** 只有新候选顺序能让原候选池之外的用户来源进入时才应用调整；保留常规检索的第一块，其余来源代表与原候选块共同交给证据打包器。
4. **保护上下文。** 沿用原文合并、邻近上下文和预算打包。文档检索、规则类查询及较小的 `top_k` 走原路径；若调整丢失原结果中的常驻规则，则回退至原结果。

检索保留各角色的文字证据，角色标签用于区分谁说了什么。日期、否定、条件和新旧陈述随所选原文保留；系统不会将多个陈述合成为未经证据支持的新事实。该版本不使用训练、生成式查询规划、图传播或 ColBERT。

## 接口与隔离边界

| 方法与路径 | 用途 | 成功响应 |
| --- | --- | --- |
| `POST /add` | 同步写入；提交完成后才返回成功 | `success`、`request_id`、`user_id`、`session_id` |
| `POST /search` | 按证据优先级返回记忆 | `{"data": [...]}`；空结果为 `{"data": []}` |
| `GET /health` | 无鉴权健康检查与服务身份 | `status` 及模型、检索配置元数据 |

- `user_id` 是隔离边界；同一用户的不同 `session_id` 可以跨会话检索。
- 同一用户内以 `request_id` 保证写入幂等；相同 ID、不同内容返回 `409`。
- Search 条数不超过请求的 `top_k`，顺序即证据优先级；只返回记忆证据，不生成答案或选项字母。
- Add / Search 使用 `x-api-key` 或 `Authorization: Bearer ...` 鉴权，真实凭据通过私密配置注入。

本发布面向 Textual 纯文本消息，`messages[].content` 为字符串，不宣称支持代码或多模态赛道。完整请求、错误行为及跨会话说明见[运行指南](scenarios/RUN_GUIDE.md)。

## 复现与运行

需要 Python 3.10+。先克隆仓库并创建环境，再从固定发布目录启动：

```bash
git clone https://github.com/gioruno-banana/usertrail-memory.git
cd usertrail-memory
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd releases/v0.69-v3-current-source
```

按[运行指南](scenarios/RUN_GUIDE.md#参评服务配置)设置私密凭据、embedding 地址和独立数据库，然后运行：

```bash
../../.venv/bin/python -m uvicorn m06_candidate:app \
  --host 127.0.0.1 --port 18404 --workers 1 --no-access-log
```

Windows 命令、HTTPS 部署、无网络演示和哈希核验也见运行指南。数据库目录必须可写；不要把数据库、密钥或评测内容上传到仓库。

## 评测状态与边界

v0.69 的 Textual Full 已提交。平台查询确认任务 `teval_4fc11cd07b9fc31d` 为 `succeeded / completed`，完成时间为 **2026-11-02 10:56:50（UTC+8）**。任务成功不等同于已通过公榜审核；正式发布状态以[赛事平台](https://agentmemories.ai/)为准。

此处不将早期研究分数、合成演示或 Smoke 结果当作本次 Full 的成绩，也不据此宣称性能提升。完整历史竞争受证据预算限制，可能带来额外查询编码、排序开销或无关证据；超长输入也受 embedding 供应商限制。源码身份与已记录修复范围见固定版本材料。

运行成本由 embedding API 调用及本地 CPU、内存、SQLite 存储构成；Add / Search 无生成式 LLM 调用。请求次数和资源边界见[参赛补充说明](SUBMISSION_v0.69.zh-CN.md#资源与成本)。
