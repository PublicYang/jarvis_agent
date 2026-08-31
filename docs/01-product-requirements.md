# Product Requirements (PRD)

> Jarvis 产品需求文档，说明为什么做、做什么、价值何在。  
> 相关文档：[Project Charter](./00-project-charter.md) · [Architecture](./02-architecture.md) · [Roadmap](./07-roadmap.md)

---

## 为什么做 Jarvis

### 问题

1. **框架黑盒**：LangGraph、CrewAI 等框架封装了 Runtime 细节，开发者难以理解 Agent 如何真正运行
2. **Demo 陷阱**：快速 Demo 无法积累生产级工程能力（状态机、质量闸门、ADR）
3. **演进不可见**：一次性生成完整项目，无法观察架构如何随能力增长而变化

### 解决方案

从零自研 Agent Runtime，按 Phase 逐步引入能力，每次变更可 Review Git Diff，文档与代码同步演进。

决策依据：[ADR-001 Runtime Self-Build](./adr/ADR-001-runtime-self-build.md)

---

## 核心能力规划

### Runtime

| 维度 | 说明 |
|------|------|
| **用户价值** | 稳定、可预测的 Agent 执行；支持取消、超时、重试 |
| **技术价值** | 主循环、状态机、生命周期管理 |
| **学习价值** | 理解 Agent 执行的底层机制 |

**交付 Phase**：Phase3（数据结构）→ Phase7（完整 Loop）

---

### Planner

| 维度 | 说明 |
|------|------|
| **用户价值** | Agent 能分解任务、选择下一步动作 |
| **技术价值** | Decision 驱动 Runtime；解耦规划与执行 |
| **学习价值** | 理解决策层如何与 LLM 协作 |

**交付 Phase**：Phase5

---

### Tool Calling

| 维度 | 说明 |
|------|------|
| **用户价值** | Agent 能调用外部能力（搜索、计算、API） |
| **技术价值** | ToolCall → Observation 闭环；Tool 可插拔 |
| **学习价值** | 理解 Agent 与 Tool 的契约与追踪 |

**交付 Phase**：Phase6

---

### Memory

| 维度 | 说明 |
|------|------|
| **用户价值** | 跨轮次记住上下文；长对话不丢失关键信息 |
| **技术价值** | 短期/长期记忆；Context 压缩 |
| **学习价值** | 理解 Context 工程与 State 分层 |

**交付 Phase**：Phase8–Phase10

---

### Workflow

| 维度 | 说明 |
|------|------|
| **用户价值** | 复杂任务分步执行；支持中断与恢复 |
| **技术价值** | Node、Edge、Parallel、Branch |
| **学习价值** | 理解工作流引擎与状态机升级 |

**交付 Phase**：Phase11–Phase13

---

### MCP

| 维度 | 说明 |
|------|------|
| **用户价值** | 标准化 Tool 发现与调用；与外部 MCP Server 集成 |
| **技术价值** | MCP Client；Tool Discovery |
| **学习价值** | 理解 Model Context Protocol 与生产集成 |

**交付 Phase**：Phase14

---

## 非功能需求

| 需求 | 说明 | Phase |
|------|------|-------|
| 可测试 | pytest 覆盖核心路径 | Phase2 起 |
| 可观察 | Logging、Tracing、Metrics | Phase15 |
| 可配置 | 环境变量、配置文件 | Phase15 |
| 文档同步 | 每 Phase 更新 docs/ | 全阶段 |
| 可接入 | Integration 协议 | Phase1 CLI → Phase14 MCP |

---

## 用户画像

| 角色 | 需求 |
|------|------|
| **学习者** | 观察每次架构演进、理解 Runtime 成长 |
| **开发者** | 基于 Interface Spec 扩展 Tool、Integration |
| **接入方** | 通过统一 Agent API 集成 Jarvis（CLI/Web/BAG 等） |

---

## 成功指标

| 指标 | 目标 Phase |
|------|------------|
| 最小 Agent 闭环 | Phase6 |
| Memory 可用 | Phase10 |
| Workflow 可回放 | Phase12 |
| MCP 集成 | Phase14 |
| 生产硬化 | Phase15 |

详见 [Quality Gates](./10-quality-gates.md) 与 [Roadmap](./07-roadmap.md)。
