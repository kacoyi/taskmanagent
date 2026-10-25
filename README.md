# Taskmanagent

面向仓库负责人的本地桌面项目理解工具：解释项目能力、结构、依赖和不确定性，
并把用户想法与可检查的证据关联起来。

A local-first desktop project understanding tool, designed around traceable
evidence and durable owner intent.

**当前处于架构设计阶段，没有可安装产品。** 仓库包含设计契约、合成验收样例和
可运行的设计校验工具。校验通过不代表产品、AI 解释质量或数据恢复能力已经实现。

首版聚焦一个明确选定的仓库和一种源码语言：只读采集、能力与依赖解释、证据查看、
想法留存、刷新状态。多仓库覆盖、任务执行、代码修改和部署控制留待后续验证。

## 本地验证

需要 Python 3.9+，只使用标准库，无需 API 密钥、AI 服务或被分析的真实仓库。
CI 检查 Python 3.9 和 3.14。

```sh
python3 tools/check_contracts.py
python3 -m unittest discover -s tests -v
```

## 从哪里开始

| 内容 | 入口 |
| --- | --- |
| 产品目标、首版边界和待定输入 | [engineering.v0.json](contracts/engineering.v0.json) |
| 模块职责、数据归属和依赖 | [architecture.v1.json](contracts/architecture.v1.json) |
| 变更路线、验收场景和阶段门禁 | [evolution.v1.json](contracts/evolution.v1.json) |
| 设计理由、代价和重新评估条件 | [decisions.v1.json](contracts/decisions.v1.json) |
| 人与 AI 的开发流程 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| AI 工作入口 | [AGENTS.md](AGENTS.md) |

下一步是验证最小闭环；目标系统、参考仓库和首个源码语言仍需确定。
源码目录只在有实际功能时创建，设计中的路径不代表已有实现。

欢迎用中文或英文提交问题与改进建议。涉及敏感内容的问题请按
[安全报告说明](SECURITY.md)处理。

## 许可证

[MIT](LICENSE)，Copyright (c) 2026 kacoyi and contributors.
