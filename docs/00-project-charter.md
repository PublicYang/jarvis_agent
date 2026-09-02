# Project Charter

> Jarvis 项目入口契约，定义使命、边界与成功标准。  
> 相关文档：[PRD](./01-product-requirements.md) · [Architecture](./02-architecture.md) · [Roadmap](./07-roadmap.md)

---

## 项目使命

按照真实生产项目的方式，从零演进出一个完整的 Agent Runtime。  
整个开发过程必须能够让开发者观察每一次架构演进、代码 Diff 和设计决策。

Jarvis 是一个**独立的 Python Agent 项目**，可以被任何客户端接入。

---

## 一句话介绍

> Jarvis 是一个使用 Python 从零实现的 Agent Runtime，用于学习生产级 Agent 的完整演进过程——不追求最快 Demo，而追求理解 Runtime 如何一步步成长。

---

## 系统定位

```text
Client
    │
    ▼
 Jarvis Agent
    │
    ▼
 Runtime
    │
    ▼
 Tools
    │
    ▼
 LLM
```

**说明：**

- **Client**：任何接入方，通过 Integration 层与 Jarvis 通信
- **Jarvis Agent**：对外暴露的统一 Agent 接口（Application 层）
- **Runtime**：执行引擎，驱动 Planner → Tool → State 主循环
- **Tools**：可插拔工具集
- **LLM**：模型适配层

### 未来 Integration（接入方）

| Integration | 类型 | 说明 |
|-------------|------|------|
| CLI | 内置 | Typer 命令行，Phase1 起 |
| Web | 外部 | HTTP/WebSocket API |
| Telegram | 外部 | Bot 接入 |
| Discord | 外部 | Bot 接入 |
| BAG | 外部 | Java Gateway，仅为 Integration 之一 |

Integration 不属于 Jarvis 核心，详见 [Project Structure — integrations/](./05-project-structure.md)。

---

## 项目边界

### Jarvis 负责

| 能力 | 文档 |
|------|------|
| Runtime | [Architecture](./02-architecture.md) · [Runtime State Machine](./04-runtime-state-machine.md) |
| Planner | [Domain Model](./03-domain-model.md) · [Interface Spec](./09-interface-spec.md) |
| Tool Calling | [Architecture](./02-architecture.md) |
| Memory | [Domain Model — MemoryRecord](./03-domain-model.md) |
| Workflow | [Roadmap V3](./07-roadmap.md#v3-workflow-engine) |
| MCP | [Roadmap V4](./07-roadmap.md#v4-production-agent) |
| Integration 协议 | [Interface Spec](./09-interface-spec.md) |

### 非目标（Out of Scope）

| 项 | 原因 |
|----|------|
| Gateway 实现 | 属于 Integration 接入方（如 BAG） |
| Bot SDK 内置 | Telegram/Discord 通过 integrations/ 适配 |
| 多租户 Session 管理 | 接入方职责 |
| 定时调度 Cron | 接入方职责 |
| 快速 Demo 交付 | 学习演进优先于速度 |

---

## 成功标准

| 标准 | 验收 |
|------|------|
| **可观察演进** | 每个 Phase 有 Expected Git Diff，Diff 可 Review |
| **文档驱动** | 所有开发以 docs/ 为唯一依据 |
| **质量闸门** | 每个 Phase 通过 [Quality Gates](./10-quality-gates.md) |
| **Agent 闭环** | Phase6 完成 Tool Calling 闭环 |
| **生产就绪** | V4 完成 Logging、Tracing、Metrics、MCP |
| **可接入** | 至少 CLI Integration 可用；协议支持外部 Client |

---

## 当前阶段

| 版本 | Phase | 状态 |
|------|-------|------|
| V0 | Phase0 Design Gate | ✅ 完成 |
| V0 | Phase1 Project Skeleton | 🔄 进行中 |

详见 [Roadmap](./07-roadmap.md)。

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [01-product-requirements.md](./01-product-requirements.md) | 产品需求 |
| [02-architecture.md](./02-architecture.md) | 分层架构 |
| [03-domain-model.md](./03-domain-model.md) | 领域模型 |
| [04-runtime-state-machine.md](./04-runtime-state-machine.md) | 状态机 |
| [05-project-structure.md](./05-project-structure.md) | 目录规划 |
| [06-tech-stack.md](./06-tech-stack.md) | 技术选型 |
| [07-roadmap.md](./07-roadmap.md) | Master Roadmap |
| [08-engineering-standards.md](./08-engineering-standards.md) | 工程规范 |
| [09-interface-spec.md](./09-interface-spec.md) | 接口规范 |
| [10-quality-gates.md](./10-quality-gates.md) | 质量闸门 |
| [11-risk-register.md](./11-risk-register.md) | 风险登记 |
| [12-development-principles.md](./12-development-principles.md) | 开发原则 |
| [adr/](./adr/) | 架构决策记录 |
