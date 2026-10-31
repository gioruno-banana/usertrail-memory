# UserTrail Memory 0.3 research candidate

完整历史的所有角色按来源相关性竞争；只有真实原生候选池之外的用户来源进入
新池时才启用，再进入未经修改的 exact 官方 0.32 原生打包。用户角色没有额外
加权，assistant 内容保留原角色。原文、日期、否定和条件不改写，不生成画像。
文档/规则查询走原路；standing rule 被丢失或改写时返回整个原版结果。

本包仅在本地准备，尚无 V3 最终答案成绩，也未发布到 GitHub。原生打包仍可能
丢失解释性上下文；完整来源参加排序不等于完整来源进入最终输入。

```powershell
python -m pip install -r requirements.txt
python verify_release.py
python -m unittest discover -s tests -v
python demo.py
```

示例只用合成记录与哈希向量。真实本地 BGE 配置和研究复现见 RUN_GUIDE.md，
身份和源码哈希见 SOURCE_PROVENANCE.json。该服务只返回证据原文，由调用方
完成回答。包中没有评测记录、答案、权重、数据库、缓存或凭据。
