# UserTrail Memory 运行指南

## 1. 安装与无模型演示

在克隆后的仓库根目录打开 PowerShell，使用 Python 3.10+：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe demo.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux/macOS 将 `.\.venv\Scripts\python.exe` 换为 `.venv/bin/python`。演示临时创建 SQLite 数据库，退出时清理；输入是仓库内的合成消息。14 项分发与候选测试验证角色、日期、否定/条件、完整上下文、全历史来源、鉴权、幂等写入、用户隔离和评测字段拒绝。演示向量是合成哈希，不能作为研究分数复现。

保留的 exact 0.32 原版 64 项测试需要在其目录运行：

```powershell
Push-Location exact32-source
..\.venv\Scripts\python.exe -m unittest discover -s tests
Pop-Location
```

## 2. 真实本地向量服务

先准备本地 `BAAI/bge-small-en-v1.5` 模型目录，至少包含配置、权重、tokenizer 等原始文件。本仓库不捆绑或自动下载权重。安装可选依赖并设置路径：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
$env:USERTRAIL_EMBEDDING_MODEL = 'D:\models\bge-small-en-v1.5'
$env:AE_DATABASE = (Join-Path $PWD 'data\usertrail.sqlite3')
$env:MEMORY_API_KEY = [guid]::NewGuid().ToString('N')
.\.venv\Scripts\python.exe -m uvicorn usertrail_service:app --host 127.0.0.1 --port 18404
```

请保持此终端运行。将路径改为自己的现有模型目录；适配器只从本地加载并使用 CPU。`MEMORY_API_KEY` 保存在当前终端环境中，调用端需使用同一值，请勿提交到 Git。若需跨终端使用，请自行通过本地私密方式设置同一密钥；不要把真实密钥写进示例或仓库。默认仅监听本机。

如仍在原研究项目中，必须先确认 18404 已空闲；模型评测/训练继续遵守项目公共 GPU 锁规则，不得关闭其他方向服务。此命令是单独的 CPU 检索服务，不启动 Answer/Judge。

## 3. 调用 Add / Search

下例可在另一个已设置相同 `$env:MEMORY_API_KEY` 的 PowerShell 中执行。时间戳是 Unix 毫秒，日期未知时省略字段；不要填造日期。`request_id` 用于幂等，重用相同 ID 但修改内容会返回 409。

```powershell
$base = 'http://127.0.0.1:18404'
$headers = @{ 'x-api-key' = $env:MEMORY_API_KEY }
$payload = @{
  request_id = 'example-1'
  user_id = 'example-user'
  session_id = 'example-session'
  messages = @(
    @{ role = 'user'; content = 'I do not eat shellfish unless my doctor clears it. Because it caused a reaction.'; timestamp = 1735689600000 },
    @{ role = 'assistant'; content = 'You could consider a simple rice meal.' }
  )
} | ConvertTo-Json -Depth 8
Invoke-RestMethod "$base/add" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
$query = @{ user_id = 'example-user'; query = 'Which shellfish meals suit my needs?'; top_k = 10 } | ConvertTo-Json
Invoke-RestMethod "$base/search" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($query))
Invoke-RestMethod "$base/health"
```

Search 返回 `data` 证据列表，每项含 `id`、原文 `content`、排序 `score`，有日期时含 `created_at`。原文中保留说话者及可用时间。上层应用应将问题和所选证据交给自己的回答模型；本服务不会生成最终答案，也不会把原文中的内容当成运行指令。API 沿用原生 `options` 可选字段；没有需要时请省略，研究补充选择只依据查询主题。`top_k` 为 1–100；候选在低于 8 时保留原检索结果。

## 4. 关闭、数据与成本

在启动服务的终端按 Ctrl+C。数据库保存在 `AE_DATABASE` 指定路径，重启使用相同路径即可恢复；不要上传数据库或模型。仓库的 `.gitignore` 排除数据、日志、权重、环境文件与虚拟环境。

Add 按原版将消息编码并存储；原生 Search 编码查询，触发用户全历史增补时再编码一次查询。没有生成调用或云调用，运行成本为本地 CPU/内存/磁盘；最终回答模型成本由调用方承担。研究中的 embedding 使用预先冻结缓存，不能把其零新增调用当成新部署中的零编码成本。

## 5. 研究复现边界

分发适配层经过合成编码器的 API 端到端验证；此发布没有额外启动真实 BGE 服务做新的模型质量评测。原版编码器源码和已评测的模型身份保留，模型权重本身需由使用者准备。`research/` 给出全部汇总、逐题结果元数据与协议说明，不含评测题目或真实输入。

576 题的最终答案比较还需要原项目冻结的公开数据、检索缓存、Qwen GGUF、原生评分实现和运行时，不能通过 `demo.py` 得到相同成绩。研究完整复现步骤保存在原项目的 `04-user-history/REPRODUCE.md` 与源码交付包；Judge 的 10240 修订及原 8192 结果分别留档。不要将此仓库的演示或单元测试视为官方评测，也不要自动提交 Smoke/Full 或晋升候选。
