# 对话历史包开发笔记

UserTrail 的历史处理与候选实现位于 `history/usertrail/`，HTTP 接入位于 `interfaces/http/`，模型锁逻辑由 `coordination.model_lock` 提供。安装后的开发服务入口为 `usertrail_service:app`。

在项目根目录创建独立虚拟环境后，安装包并运行场景测试：

```shell
python -m pip install -e .
python -m unittest discover -s scenarios/tests -p "test_*.py"
python scenarios/history_demo.py
```

测试与演示使用合成消息及模拟编码器。实际 HTTP 运行方式见 [RUN_GUIDE.md](RUN_GUIDE.md)；凭据和运行数据库应与开发场景分开保存。

冻结发布树与当前开发文件有各自的核验入口：

```shell
python scenarios/verify_release.py
python scenarios/verify_release.py --development
python scenarios/verify_layout.py
python scenarios/verify_layout.py --frozen-only
```

第一条核验固定发布树，带 `--development` 的命令核验开发树；后两条按开发文件清单或受保护文件清单核对哈希。固定运行源码保存在 `releases/`，基础依赖位于 `upstream/exact32/`。开发安装与场景测试不改变这些版本的身份。

历史实验记录在 `studies/` 中保留原范围，项目与依赖许可见根目录 [LICENSE](../LICENSE) 及 `upstream/` 的许可文件。
