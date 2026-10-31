# UserTrail Memory v0.69：来源与复现草稿

拟参赛成员：郑俊烽；所属机构：北京理工大学。该信息由参赛者提供，本草稿尚未写入平台。

当前m06的算法是V3全历史用户来源竞争。它基于SourceTrail / Context Weave exact0.32.0，原作者王子铭（Giorno-Banana），MIT；原代码、许可证与来源说明保留在源包中。新增部分属于本轮衍生修改，不将上游全文声称为本团队原创。上游来源见[PROVENANCE.md](releases/v0.69-v3-current-source/exact32-source/PROVENANCE.md)，研究冻结身份见[SOURCE_PROVENANCE.json](releases/v0.69-v3-current-source/SOURCE_PROVENANCE.json)。

V3保留原生文档/规则/多事件路径，从完整用户历史提出原文来源，并在固定预算中竞争进入证据包；保留说话者、日期、否定、条件和新旧陈述，不将assistant建议转为用户偏好。Add/Search无生成LLM，真实服务使用text-embedding-v4、1024维、batch10，query_document_evidence、24,000字符。平台统一负责最终Answer和Judge。

这不是已验证胜出的最终候选。V3两次官方Smoke为60.2430556和65.625，均46/46完整结束，均值62.9340278；同账号原版为65.625和60.7638889，均值63.1944444。V3第二轮G55，首轮G30；两次官方题目身份不公开，不能作配对归因或仅挑最高一次。V3本地完整最终答案对照尚未结束，永久门槛没有通过证据。不能把V1/V2成绩移作V3成绩；Full未提交。

源码目录releases/v0.69-v3-current-source/逐字来自当前部署归档：SHA256 18eafab34b1a242e27311193ee01e2f4941f8dc501a0c0914839a3b5ac78b613；candidate.py SHA256 7c42aab6055539082b3a0650b83d15d58bb2749f9851e1d4713a80660fdd951d。RELEASE_MANIFEST.json为逐文件身份。公开仓库旧根目录仍代表V1；运行当前V3时必须进入上述子目录，不能运行根目录旧适配器。

独立运行需要Python3.10+、requirements.txt中的固定依赖。先建立独立venv和私有环境文件，设置MEMORY_API_KEY、DASHSCOPE_API_KEY及官方embedding URL、AE_DATABASE绝对私有路径、AE_EMBEDDING_BACKEND=dashscope、AE_EMBEDDING_DIMENSIONS=1024、AE_EMBEDDING_BATCH_SIZE=10、AE_CONTEXT_CHARS=24000、AE_MODE=query_document_evidence；不启用其他生成或索引组件。在该子目录运行 `python -m uvicorn m06_candidate:app --host 127.0.0.1 --port 18106 --workers 1 --no-access-log`，反向代理以TLS提供已登记的/m06/add、/m06/search、/m06/health，传入X-Api-Key或Bearer认证。认证值不写入公开文件。

现有服务器由systemd的memory-lab@m06.service管理，仅使用自有独立源码目录和drop-in；不得修改十套共用源码或其他实例。更新须先核对全部任务空闲、声明新源码身份、保存当前版本及DB备份，再只重启m06。Full受理后冻结算法/模型/配置，不能在运行中按部分成绩改变行为。

用户隔离以user_id为边界，同user不同session可跨会话检索；request_id在user范围内幂等，冲突正文返回409；同步Add在原子持久化后才成功，Search顶层data有序且不超过top_k，空空间返回data:[]。Search仅返回来源证据，不生成答案或选项。语义无关阈值尚未验证，不承诺无关查询必返回空数组。

本草稿只包含源码及说明，不含凭证、数据库、真实历史、评测题/答案、请求缓存或模型权重。官方任务数据仅在授权服务内用于当前任务，完成后30天内删除，不用于训练或公开传播。真实embedding和评测token费用未知，由参赛者承担服务侧成本。Full开始后该账号该赛道不再开放Smoke。

归档内SOURCE_PROVENANCE.json的local_only、no_official_submissions等字段描述研究包冻结时的阶段；不代表后续没有官方Smoke。README_M06.md中小时探索授权也是打包时记录，最新项目准入重新要求完整本地配对与永久门槛。归档文件为保持部署身份逐字不改，以本说明披露后续状态。

磁盘沿用现有共享卷，不设5G硬配额、不自动购买。历史同源Full主库约3.09GiB，不是本次峰值上限；备份另计。当前已有容量预警，空间不足由参赛者升级。最新服务窗口Search均值2.157s、P95 6.91s、最大7.78s，134 Add/48 Search均200；这些为middleware计时，不是平台端到端延迟。Add/Search生成LLM调用0，实际embedding费用和官方token账单未知。

本地Git发布草稿尚未推送；它包含现有m06部署的相同源码，未因此重启或更改线上方法。Full最终批准、项目性能门槛和赛事方复核是不同事项，不能由平台技术准入推定全部满足；须在最后人工确认后才可能正式提交。
