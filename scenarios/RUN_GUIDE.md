# UserTrail Memory v0.69 运行指南

参评服务在 `releases/v0.69-v3-current-source/`，入口为 `m06_candidate:app`。仓库根目录的 `usertrail_service:app` 是早期本地研究适配器，不能用它替代参评入口。本指南使用隔离的本地端口与新的测试数据库。

## 安装

需要 Python 3.10+、可写磁盘及可访问 `text-embedding-v4` 的供应商账号。依赖版本锁定在 `requirements.txt`。从仓库根目录运行：

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows PowerShell 将 `.venv/bin/python` 换为 `.\.venv\Scripts\python.exe`。逐字复现固定源码时，可另行检出 README 中的源码 commit；后续文档 commit 不代表新的检索版本。

## 参评服务配置

| 环境变量 | v0.69 配置或含义 |
| --- | --- |
| `MEMORY_API_KEY` | 必填；部署方设置的 Add / Search 鉴权密钥 |
| `DASHSCOPE_API_KEY` | 必填；embedding 供应商密钥，与赛事账号及接口密钥分别管理 |
| `AE_EMBEDDING_BACKEND` | `dashscope` |
| `AE_EMBEDDING_URL` | 必填；供应商的 DashScope 原生 text-embedding HTTPS 地址，不含密钥 |
| `AE_EMBEDDING_DIMENSIONS` | `1024` |
| `AE_EMBEDDING_BATCH_SIZE` | `10` |
| `AE_EMBEDDING_TIMEOUT` | 单次 embedding 请求超时，默认 `60` 秒 |
| `AE_EMBEDDING_MAX_ATTEMPTS` | 单次 embedding 请求最大尝试次数，默认 `3` |
| `AE_EMBEDDING_MAX_REQUESTS` | 进程级请求预算，`0` 表示不设置该预算上限 |
| `AE_DATABASE` | 独立 SQLite 绝对路径；父目录需可写 |
| `AE_MODE` | `query_document_evidence` |
| `AE_CONTEXT_CHARS` | `24000`；证据字符预算，不是 Answer 模型的 token 窗口 |

以下示例生成本地测试接口密钥，隐藏读取供应商密钥。生产环境应由权限受控的环境文件或秘密管理工具注入。embedding 地址需匹配账号区域和 DashScope 原生协议，不能直接替换为 OpenAI 兼容 schema。

Linux/macOS，从仓库根目录执行：

```bash
mkdir -p data
export MEMORY_API_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
read -r -s -p 'Embedding provider key: ' DASHSCOPE_API_KEY
export DASHSCOPE_API_KEY
printf '\n'
read -r -p 'DashScope native embedding HTTPS URL: ' AE_EMBEDDING_URL
export AE_EMBEDDING_URL
export AE_EMBEDDING_BACKEND=dashscope
export AE_EMBEDDING_DIMENSIONS=1024
export AE_EMBEDDING_BATCH_SIZE=10
export AE_DATABASE="$PWD/data/usertrail-v069.sqlite3"
export AE_MODE=query_document_evidence
export AE_CONTEXT_CHARS=24000
cd releases/v0.69-v3-current-source
../../.venv/bin/python -m uvicorn m06_candidate:app \
  --host 127.0.0.1 --port 18404 --workers 1 --no-access-log
```

Windows PowerShell，从仓库根目录执行：

```powershell
New-Item -ItemType Directory -Path data -Force | Out-Null
$env:MEMORY_API_KEY = [guid]::NewGuid().ToString('N')
$credential = Read-Host 'Embedding provider key' -AsSecureString
$env:DASHSCOPE_API_KEY = [System.Net.NetworkCredential]::new('', $credential).Password
$env:AE_EMBEDDING_URL = Read-Host 'DashScope native embedding HTTPS URL'
$env:AE_EMBEDDING_BACKEND = 'dashscope'
$env:AE_EMBEDDING_DIMENSIONS = '1024'
$env:AE_EMBEDDING_BATCH_SIZE = '10'
$env:AE_DATABASE = Join-Path $PWD 'data\usertrail-v069.sqlite3'
$env:AE_MODE = 'query_document_evidence'
$env:AE_CONTEXT_CHARS = '24000'
Set-Location releases/v0.69-v3-current-source
..\..\.venv\Scripts\python.exe -m uvicorn m06_candidate:app --host 127.0.0.1 --port 18404 --workers 1 --no-access-log
```

单 worker 保存进程内索引与锁，不要直接改成多 worker。使用相同绝对数据库路径重启可复用持久化数据；向量身份不匹配时应使用匹配配置或另一个数据库，不能删除正式评测数据来绕过检查。

## Add / Search 示例

在第二个 PowerShell 终端通过私密方式设置相同的 `MEMORY_API_KEY`，不要打印密钥。以下数据均为合成示例；时间戳是 Unix 毫秒，日期未知时省略。

```powershell
$base = 'http://127.0.0.1:18404'
$headers = @{ 'x-api-key' = $env:MEMORY_API_KEY }
$write = @{
  request_id = 'example-write-1'
  user_id = 'example-user'
  session_id = 'session-1'
  messages = @(
    @{ role = 'user'; content = 'I do not eat shellfish unless my doctor clears it. It caused a reaction.'; timestamp = 1735689600000 },
    @{ role = 'assistant'; content = 'You could consider a simple rice meal.' }
  )
} | ConvertTo-Json -Depth 8
Invoke-RestMethod "$base/add" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($write))
$query = @{ user_id = 'example-user'; query = 'What food restrictions have I mentioned?'; top_k = 100 } | ConvertTo-Json
Invoke-RestMethod "$base/search" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($query))
Invoke-RestMethod "$base/health"
```

Add 成功响应：

```json
{"success": true, "request_id": "example-write-1", "user_id": "example-user", "session_id": "session-1"}
```

Search 顶层为 `data` 数组，条目含 `id`、原文 `content`、排序 `score`，有日期时含 `created_at`，最多 `top_k` 项。空库用户返回 `{"data": []}`。Search 不要求 `session_id`，可检索同一用户此前写入的其他会话；其他用户记录不进入该用户索引。

`request_id` 在同一用户内幂等：同 ID、同请求重复 Add 不重复写入；内容冲突返回 `409`。原文、向量和请求状态提交并更新检索可见性后，Add 才返回成功。重试应保持原 ID 与请求体。

鉴权缺失或错误返回 `401`，schema 校验错误返回 `422`，embedding 失败可返回 `503` 并携带 `Retry-After`。`top_k` 必须是 1–100 的整数。可选 `options` 沿用平台 schema，本候选不据选项生成答案；不得传入金标或评分字段。此服务实现 Textual 字符串消息，不宣称支持多模态内容数组。

## HTTPS、数据与资源

本地 uvicorn 仅监听回环地址，应用提供 `/add`、`/search`、`/health` 相对路由。访问基址和 HTTPS 接入由独立运行环境配置。

应用与数据库使用独立目录和最小文件权限；可由 systemd 按上述工作目录、私密环境及单 worker 命令启动。`GET /health` 的 `X-UserTrail-Candidate-SHA256` 响应头可与 README 核对。日志不应记录请求正文或鉴权。

停止本地服务使用 Ctrl+C。正式升级前需确认任务状态、版本冻结要求、一致数据库备份与回滚配置。容量覆盖 SQLite 主库、WAL、索引缓存与备份，按实际负载监测，不承诺固定磁盘或内存上限。费用来自 embedding API 和部署资源；本服务无生成式 LLM 调用。

## 离线演示与完整性核验

从仓库根目录运行：

```bash
.venv/bin/python scenarios/history_demo.py
.venv/bin/python scenarios/verify_release.py
.venv/bin/python -c "from pathlib import Path; import hashlib; print(hashlib.sha256(Path('releases/v0.69-v3-current-source/candidate.py').read_bytes()).hexdigest())"
```

Windows 使用 `.\.venv\Scripts\python.exe`。演示使用临时 SQLite 和合成哈希向量，无真实评测数据、网络或生成式模型调用；这是早期研究适配器示例，不复现 v0.69 模型质量或 Full 分数。`scenarios/verify_release.py` 核验分发清单和冻结文件身份，候选哈希预期值见 README。

`studies/`、根目录本地 BGE 适配器及发布目录内的早期研究 README/元数据均为归档；当前参评运行配置以本指南为准。仓库不分发评测问题、答案、金标、数据库、模型权重或服务秘密，也不包含自动提交 Smoke / Full 的工具。
