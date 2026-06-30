# 文档维护规则

> 代码变更后，按下表检查并更新相关文档。文档与代码不一致是技术债的源头。
> **契约真相源是 [AGENTS.md](../../AGENTS.md)**（CLAUDE.md 经 `@AGENTS.md` 导入）；改契约只改 AGENTS.md，不要在 CLAUDE.md 另起副本。

## 同步映射表

| 改动 | 必须同步 |
|------|----------|
| 新增/删除/重命名模块或包 | [AGENTS.md](../../AGENTS.md) 包结构；[doc/architecture/overview.md](../../doc/architecture/overview.md) 包结构；[README.md](../../README.md) 项目结构 |
| 改依赖方向 / 层边界 | [AGENTS.md](../../AGENTS.md) 分层表（**权威副本**）；[doc/architecture/boundaries.md](../../doc/architecture/boundaries.md) 证据 |
| 新增/消除架构债 | [AGENTS.md](../../AGENTS.md)「已知债」表（**唯一权威清单**，其余文档只链接，不另列） |
| 新增/升级/移除依赖 | `pyproject.toml`；[AGENTS.md](../../AGENTS.md) 技术基线表 |
| 改启动方式 / 入口 | [README.md](../../README.md) 快速开始；[AGENTS.md](../../AGENTS.md) 场景锚点 + 常用命令 |
| 改 MCP 工具 / 桥 / 端口 | `src/autogame_xcx/mcp/` 内注释；客户端侧 [../wechat-ilink-bot/docs/design/mcp-autogame.md](../../../wechat-ilink-bot/docs/design/mcp-autogame.md) |
| 新增/重构 UI 页面 | [AGENTS.md](../../AGENTS.md) 包结构 + 场景锚点；[ui-conventions.md](ui-conventions.md)；与设计稿对照记录差异 |
| 改测试约定 / marks / fixture | [testing.md](testing.md) |
| 改编码约定 | [python-conventions.md](python-conventions.md) 或 [ui-conventions.md](ui-conventions.md) |
| 项目方向 / 阶段推进 | [doc/ROADMAP.md](../../doc/ROADMAP.md) |

## 防漂移约定（harness 与代码保持同步）

1. **不在散文里硬编码行号**：定位用"文件 + 符号/函数/分支名"（如"`process_main.py` 的 `--gui` 分支"），行号会随编辑漂移。
2. **单一权威 home**：分层图 / 依赖方向 / 已知债表各只有一个权威副本（均在 AGENTS.md），其余文档**链接而非重述**。
3. **完成态用过去式**：已完成的阶段/重构写过去式 + ✅，不在已完成项上留"待 Phase X 拆分"之类的将来时。
4. **报告类文档带日期 + 状态**：核验/快照类文档（如 verification_report）顶部标生成日期与状态；过期即归档到 `doc/archive/` 并在原位留指针，不留半真半假内容。
5. **文件行数/体量例外**：单文件超 500 行的例外只登记在 AGENTS.md 已知债表，删除/拆分后同步移除该条。

## 守则

- 文档改动同样 surgical：只更与代码变更直接相关的段落，不顺手改无关内容。
- 新增 public 类/函数若行为不直观，在模块 docstring 或对应 design 文档记一笔。
