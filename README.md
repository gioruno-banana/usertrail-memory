# UserTrail Memory · 用户原文证据记忆

UserTrail Memory 从完整历史中寻找与当前问题有关的用户原文，为解释原因、条件、否定和不同日期的陈述保留证据。它先运行 exact SourceTrail 0.32 的检索与打包，再按固定规则补充用户来源。返回的是原文证据；最终回答由调用方自己的模型生成。

**版本：0.1.0-research。研究结论：尚未验证优于 exact 0.32，拒绝用于替换 incumbent。** 这是可复现研究候选的发布，不是高分或生产效果保证；未提交新的 Smoke/Full，也未自动晋升。

## 快速运行

需要 Python 3.10 或更新版本。在仓库根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe demo.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

演示仅使用合成对话和确定性哈希向量，无需模型、账号或网络。它用于验证接口与原文保留，不能代表 BGE 检索质量。运行真实本地向量服务、调用 `/add` 和 `/search`、停止服务及复现测试的完整步骤见 [RUN_GUIDE.md](RUN_GUIDE.md)。

## 固定机制

- 保留 exact 0.32 的原版 Search、文档识别、规则路径及 24,000 字符 / top100 上限。
- 扫描全部原始 user 来源，突破初始 128 候选池；查询词面主题覆盖结合既有向量相似度。
- 最多选择 4 个来源，补充总预算为 3,600 字符；短消息完整保留，长消息保留完整匹配句和解释邻句。
- 保留角色、日期、否定、条件，以及相关的新旧陈述；增补过程只选 user 原文，不把 assistant 建议转成偏好或推断画像。原版已有的其他角色证据仍可正常检索。
- 原版首项及 standing-rule 命中项之后才插入；原预算内的增补仍可能挤出尾部证据，所有这类变化均计入研究审计。

不进行训练、图传播、程序提取、ColBERT 或多轮查询。Add/Search 没有生成模型调用。本发布适配器只允许显式指定本地 BGE 目录，默认 CPU；候选触发增补时会额外调用一次查询编码。研究实验使用既有缓存，因此没有新 embedding 请求。

## 最终答案研究结果

固定六数据集、每个 development/holdout 各 48 题，共 576 题、两臂 1,152 条有效评分。公开分割已有历史曝光，不是新的盲测。

| 范围 | exact 0.32 | UserTrail | 胜 / 负 / 平 |
|---|---:|---:|---:|
| development 宏平均 | 43.0556% | 42.7083% | 1 / 2 / 285 |
| holdout 宏平均 | 45.8333% | 46.1806% | 3 / 2 / 283 |
| 全体宏平均 | 44.4444% | 44.4444% | 4 / 4 / 568 |

97/576 道题的实际 Answer 输入改变。8 道选到初始 128 候选之外的来源，其中 4 道真正把池外新文本送入最终输入。277 道已标注题的 Search/input 召回全部持平，未满足至少一道已标注输入覆盖增益的要求。个性化总分持平；偏好推荐有一负，建议新想法有一胜。LongMem development 26→25/48，永久回归门槛失败。

Answer/Judge 使用本地 Qwen3.5-4B Q4_K_M。为完整评分，用户授权将全部 CL 的 Judge 上下文统一从 8192 改到 10240：所有既有答案固定，两臂全部 192 条 CL 统一重评，其他数据集保持原评分；补齐两条，原有效 CL 分数均未变。这是观察初步结果后的独立协议修订，不是独立重复实验。完整逐数据集成绩、所有胜负、成本与局限见 [research/RESULTS.md](research/RESULTS.md)。

## 文件与出处

`candidate.py` 是冻结的研究实现，SHA256 为 `1639d2ec45464ac94af6a443c59509b9e85c8aecaff4028d86c320de31a44c78`；`exact32-source/` 的保留文件逐字来自 incumbent 指定归档。`usertrail.py`、`demo.py`、`usertrail_service.py` 是独立使用的分发适配层，没有改变研究候选。身份和逐文件哈希见 [SOURCE_PROVENANCE.json](SOURCE_PROVENANCE.json)。

MIT 许可，保留原作者王子铭及 exact 0.32 的来源说明。仓库不包含真实历史、评测问题/答案、数据集、数据库、模型权重、密钥或请求缓存。
