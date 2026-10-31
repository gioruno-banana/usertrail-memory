# m06：UserTrail Memory 当前 V3 探索候选

此包把冻结 V3 source-competition 接入 exact 0.32 原生 HTTP API 和原生
encoder_from_env，继续使用 m06 已配置的 text-embedding-v4 / 1024 维 / batch10、
query_document_evidence 和 24000 字符预算。没有改 V3 candidate.py 或 exact32
模块，不改 Answer/Judge、提示、数据或评分，也不换本地研究模型。

`m06_candidate:app` 在原生 API 启动前将 MemoryStore 指向冻结 V3 的子类，
Add、鉴权、输入 schema、原文数据库和 Search 响应结构继续使用原版处理器。
Health 版本及响应头公布候选身份，不把未完成评分的机制写成已验证提升。
研究原始 standalone 的本地 BGE 启动指南保留；云端 m06 使用本文件的入口。

独立目录部署并仅覆盖 memory-lab@m06.service 的 WorkingDirectory/ExecStart：
`/opt/memory-lab/venv/bin/python -m uvicorn m06_candidate:app --host 127.0.0.1 --port ${PORT} --workers 1 --no-access-log`。
保留 /etc/memory-lab/m06.env、/var/lib/memory-lab/m06、18106 及注册 URL。
不得改共享源码或共享 unit。切换前须官方任务空闲、保留一致数据库备份及
原配置身份；失败时只撤回自己创建的 m06 override，再恢复原版服务。

当前 V3 本地固定配对仍未完成。用户于 2026-10-31 明确选择每小时测试正在
优化的代码，因此本次是探索性官方 Smoke；不豁免完整本地结算或永久晋升
门槛，不自动晋升、Full 或 Git 推送。所有收益和回退均需保留。
