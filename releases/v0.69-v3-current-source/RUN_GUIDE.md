# 运行与复现

Python 3.10+。安装 requirements.txt 后运行 README 中的离线合成示例。
DemoEncoder 只验证软件行为，不能用于复现已冻结的本地模型对照。

真实服务须显式选择已存在的本地 BGE 路径，并使用独立数据库。确认自己的
18404 端口空闲后启动：

```powershell
python -m pip install -r requirements-local.txt
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:USERTRAIL_EMBEDDING_MODEL='D:\models\bge-small-en-v1.5'
$env:AE_DATABASE='data/usertrail-v3.sqlite3'
$env:MEMORY_API_KEY=[guid]::NewGuid().ToString('N')
python -m uvicorn usertrail_service:app --host 127.0.0.1 --port 18404
```

GET /health；POST /add 和 /search 需 x-api-key。add 字段为 user_id、session_id、
request_id、messages；message 保留 role、content 与可选 timestamp（毫秒）。
search 字段为 user_id、query、top_k、可选 options。Search 不接受评测答案。
相同 request_id 的一致写入幂等，冲突返回 409。每次启动须自行保管密钥；
环境变量不会自动传入另一个命令行。以上命令只绑定 localhost。

原项目中的研究运行：先核验 v3-source-competition/run.py freeze 和
evaluate.py freeze；CPU retrieval 保留原定 development/holdout 各 288 题。
完成 V2 FINALIZATION 后才能运行 V3 evaluate.py run，保持单一控制器。
V3 使用全新本地响应数据库，不借用 V1/V2 输出。全部评分有效后运行 finalize.py。

固定 Qwen3.5-4B Q4_K_M、llama.cpp b11146。Answer 与非 CL Judge 上下文 8192，
全部 CL Judge 使用已授权 10240；4096 HF 输入、512 输出、温度 0、seed
20261030、thinking off，原始提示和原生评分不变。GPU 调用须原子取得公共
local-model.lock，每批最多 24 臂，只清理自有服务和锁，禁止并行启动另一
控制器。原始数据和模型需要本地固定快照，本源码包不自带 benchmark。

最终答案尚未完成，不能把 CPU 检索覆盖变化或合成示例当成得分提升。
公开的 0.1 研究总体宏平均持平，其成绩不能归到 V3。原生打包可能损失条件、
解释和多事件上下文；必须报告全部实际输入区间和最终答案回退。
无 Smoke/Full、自动晋升、共享服务变更或 Git 推送。
