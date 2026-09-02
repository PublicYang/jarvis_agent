# Jarvis Agent

> 独立的 Python Agent Runtime，从零演进，可被任何 Client 接入。

---

## 项目介绍

Jarvis 是一个 **独立的 Python Agent 项目**，按照真实生产项目的方式，从零演进出完整 Agent Runtime。

- **语言**：Python 3.12
- **定位**：Agent Runtime 内核，非 Demo
- **原则**：可观察每一次架构演进、Git Diff 和设计决策

```text
Client → Jarvis Agent → Runtime → Tools → LLM
```

详细说明：[Project Charter](docs/00-project-charter.md)

---

## 当前版本

| 版本 | Phase | 状态 |
|------|-------|------|
| **V0** | Phase0 Design Gate | ✅ 完成 |
| **V0** | Phase1 Project Skeleton | ✅ 完成 |
| **V0** | Phase2 Dev Infrastructure | ✅ 完成 |
| **V0** | Phase3 Runtime Foundation | ✅ 完成 |

**V0 Foundation 已完成。** 下一 Phase：**Phase4 LLM Adapter**

---

## Roadmap

| 版本 | 内容 | Phase |
|------|------|-------|
| **V0 Foundation** | 设计、骨架、Dev Infra、Runtime 数据结构 | Phase0–3 |
| **V1 Core Runtime** | LLM、Planner、Tool、完整 Loop | Phase4–7 |
| **V2 Stateful Agent** | Memory、Context、Persistence | Phase8–10 |
| **V3 Workflow Engine** | Node/Edge、Interrupt、Parallel | Phase11–13 |
| **V4 Production Agent** | MCP、Logging/Tracing/Metrics | Phase14–15 |

完整路线图：[Master Roadmap](docs/07-roadmap.md)

---

## 开发原则

- **小步提交**：一个 commit 一个能力
- **一个 Phase 一个能力**：严格按 Roadmap 推进
- **Review Git Diff**：每次提交必须 Review Diff
- **文档驱动**：`docs/` 为唯一依据
- **可重构**：重构必须更新 ADR

详见 [Development Principles](docs/12-development-principles.md)

---

## 未来 Integration

Jarvis 可被任何 Client 接入。Integration 不属于核心，仅为接入层：

| Integration | 说明 | Phase |
|-------------|------|-------|
| CLI | Typer 命令行 | Phase1/7 |
| Web | HTTP API | 未来 |
| Telegram | Bot 接入 | 未来 |
| Discord | Bot 接入 | 未来 |
| BAG | Java Gateway，仅为接入方之一 | 未来 |

BAG **不是** Jarvis 的父项目。

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [00-project-charter.md](docs/00-project-charter.md) | 项目契约 |
| [01-product-requirements.md](docs/01-product-requirements.md) | PRD |
| [02-architecture.md](docs/02-architecture.md) | 架构 |
| [03-domain-model.md](docs/03-domain-model.md) | 领域模型 |
| [04-runtime-state-machine.md](docs/04-runtime-state-machine.md) | 状态机 |
| [05-project-structure.md](docs/05-project-structure.md) | 目录规划 |
| [06-tech-stack.md](docs/06-tech-stack.md) | 技术选型 |
| [07-roadmap.md](docs/07-roadmap.md) | Master Roadmap |
| [08-engineering-standards.md](docs/08-engineering-standards.md) | 工程规范 |
| [09-interface-spec.md](docs/09-interface-spec.md) | 接口规范 |
| [10-quality-gates.md](docs/10-quality-gates.md) | 质量闸门 |
| [11-risk-register.md](docs/11-risk-register.md) | 风险登记 |
| [12-development-principles.md](docs/12-development-principles.md) | 开发原则 |
| [adr/](docs/adr/) | ADR-001 ~ ADR-003 |

---

## 快速开始

Phase0 仅含文档与骨架，无可运行 Agent 代码。

```bash
cd jarvis_agent
ls docs/          # 阅读 Master Plan
```

Phase2 起：

```bash
uv sync --extra dev
uv run pytest
```

---

## License

TBD