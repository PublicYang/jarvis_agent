# Master Roadmap

> Jarvis 完整演进路线图，所有开发的唯一进度依据。  
> 相关文档：[PRD](./01-product-requirements.md) · [Quality Gates](./10-quality-gates.md) · [Development Principles](./12-development-principles.md)

---

## 总览

```text
V0 Foundation          V1 Core Runtime       V2 Stateful Agent    V3 Workflow Engine    V4 Production
─────────────────────────────────────────────────────────────────────────────────────────────────────
Phase0  Design Gate    Phase4  LLM Adapter    Phase8  Memory       Phase11 Workflow      Phase14 MCP
Phase1  Skeleton       Phase5  Planner        Phase9  Context       Phase12 StateMachine  Phase15 Hardening
Phase2  Dev Infra      Phase6  Tool Calling   Phase10 Persistence Phase13 Parallel
Phase3  Runtime Data   Phase7  Runtime Loop
```

---

# V0 Foundation

## Phase0 — Design Gate

| 项 | 内容 |
|----|------|
| **Goal** | 完成 Master Plan 全部设计文档 |
| **Deliverables** | docs/ 全套；ADR；Quality Gates；Interface Spec |
| **Learning Focus** | 生产级 Agent 项目的设计流程 |
| **Architecture Changes** | 无代码；建立分层架构文档 |
| **Expected Git Diff** | 仅 `docs/`、`README.md`、`.gitignore`、`pyproject.toml` |
| **Quality Gate** | Master Plan Checklist 全部 ✅；文档交叉引用完整 |

**状态**：✅ 完成

---

## Phase1 — Project Skeleton

| 项 | 内容 |
|----|------|
| **Goal** | 建立项目骨架，不写业务逻辑 |
| **Deliverables** | 空包目录（`__init__.py`）；`integrations/cli/` 占位；pyproject 包配置 |
| **Learning Focus** | Python 包结构；uv 项目布局 |
| **Architecture Changes** | Application 层目录出现 |
| **Expected Git Diff** | `runtime/__init__.py` 等空包；`integrations/cli/__init__.py`；pyproject 更新 |
| **Quality Gate** | `uv sync` 成功；目录与 [Project Structure](./05-project-structure.md) 一致 |

**状态**：✅ 完成

---

## Phase2 — Development Infrastructure

| 项 | 内容 |
|----|------|
| **Goal** | 建立开发工具链 |
| **Deliverables** | pytest、Ruff、Black、pre-commit 配置；`tests/conftest.py` |
| **Learning Focus** | 工程化基础设施 |
| **Architecture Changes** | Infrastructure 层工具链 |
| **Expected Git Diff** | `.pre-commit-config.yaml`；`pyproject.toml` dev 依赖；示例空测试 |
| **Quality Gate** | `pytest`、`ruff`、`black --check` 全绿；pre-commit 可运行 |

**状态**：✅ 完成

---

## Phase3 — Runtime Foundation

| 项 | 内容 |
|----|------|
| **Goal** | 第一批 Runtime 数据结构 |
| **Deliverables** | `Message`、`State`、`Task` Pydantic 模型；单元测试 |
| **Learning Focus** | Domain 对象设计；State 生命周期 |
| **Architecture Changes** | Runtime 层首次有代码；State 状态 enum |
| **Expected Git Diff** | `runtime/models.py`；`tests/runtime/test_models.py`；Domain Model 同步 |
| **Quality Gate** | 模型测试通过；不调用 LLM；文档 [Domain Model](./03-domain-model.md) 同步 |

**状态**：✅ 完成

---

# V1 Core Runtime

## Phase4 — LLM Adapter

| 项 | 内容 |
|----|------|
| **Goal** | 建立模型适配层 |
| **Deliverables** | `LLMAdapter` 接口；OpenAI 兼容实现；mock 测试 |
| **Learning Focus** | LLM API 抽象；Provider 解耦 |
| **Architecture Changes** | LLM Adapter 层落地 |
| **Expected Git Diff** | `llm/adapter.py`、`llm/openai_compat.py`；httpx 依赖 |
| **Quality Gate** | Adapter 接口测试（mock HTTP）；[Interface Spec — LLM](./09-interface-spec.md) 一致 |

---

## Phase5 — Planner

| 项 | 内容 |
|----|------|
| **Goal** | 第一次出现 Planner |
| **Deliverables** | `Planner` 接口；`PlannerOutput` 模型；SimplePlanner 实现 |
| **Learning Focus** | Decision 类型；Planner 与 State 只读协作 |
| **Architecture Changes** | Planning 层落地 |
| **Expected Git Diff** | `planner/base.py`、`planner/simple.py`；Planner 单元测试 |
| **Quality Gate** | Planner 输出 Pydantic 校验；状态图 Planning 状态可测 |

---

## Phase6 — Tool Calling

| 项 | 内容 |
|----|------|
| **Goal** | 第一次形成 Agent 闭环 |
| **Deliverables** | `Tool`、`ToolRegistry`；示例 Tool；ToolCall/Observation；WaitingTool 循环 |
| **Learning Focus** | Tool 抽象；Observation 驱动下一轮 Planning |
| **Architecture Changes** | Execution + Tools 层；数据流闭环 |
| **Expected Git Diff** | `tools/` 模块；Runtime 最小 Loop（Planning→Tool→Planning→Reply） |
| **Quality Gate** | ToolCall 可追踪；闭环集成测试；[Architecture 数据流](./02-architecture.md) 可验证 |

---

## Phase7 — Runtime Loop

| 项 | 内容 |
|----|------|
| **Goal** | 完整 Runtime 主循环 |
| **Deliverables** | `RuntimeEngine`；Retry、Timeout、Cancel、Approval；Typer CLI `chat` |
| **Learning Focus** | 状态机实现；边界条件处理 |
| **Architecture Changes** | Runtime 层完整；Application CLI 可用 |
| **Expected Git Diff** | `runtime/engine.py`、`runtime/state_machine.py`；CLI 命令 |
| **Quality Gate** | [Runtime State Machine](./04-runtime-state-machine.md) 与实现同步；CLI 单次对话可用 |

---

# V2 Stateful Agent

## Phase8 — Memory Foundation

| 项 | 内容 |
|----|------|
| **Goal** | 短期记忆 |
| **Deliverables** | `MemoryRecord`；`MemoryStore` 内存实现 |
| **Learning Focus** | State vs Memory 职责分离 |
| **Architecture Changes** | Memory 层；State.memory_refs |
| **Expected Git Diff** | `memory/store.py`；Memory 读写测试 |
| **Quality Gate** | Memory 读写一致；[Risk — Memory 污染](./11-risk-register.md) 缓解验证 |

---

## Phase9 — Context Engineering

| 项 | 内容 |
|----|------|
| **Goal** | Context Builder |
| **Deliverables** | `ContextBuilder`；Token 预算；滑动窗口/摘要策略 |
| **Learning Focus** | Context 压缩；Planner Context 输入 |
| **Architecture Changes** | Planning 层消费 ContextBuilder |
| **Expected Git Diff** | `memory/context.py`；压缩策略测试 |
| **Quality Gate** | 长对话压缩后 Planner 仍可决策；[Risk — Context 无限增长](./11-risk-register.md) 缓解 |

---

## Phase10 — Persistence

| 项 | 内容 |
|----|------|
| **Goal** | SQLite 持久化 |
| **Deliverables** | `SQLiteMemoryStore`；Session 恢复 |
| **Learning Focus** | 持久化与 Memory 接口 |
| **Architecture Changes** | Infrastructure 持久化 |
| **Expected Git Diff** | `memory/sqlite.py`；持久化集成测试 |
| **Quality Gate** | 重启后 Memory 可恢复；读写一致 |

---

# V3 Workflow Engine

## Phase11 — Workflow Foundation

| 项 | 内容 |
|----|------|
| **Goal** | Node、Edge、Transition |
| **Deliverables** | `WorkflowNode`、`WorkflowEdge`；简单线性 Workflow |
| **Learning Focus** | 图结构；Task.subtasks 扩展 |
| **Architecture Changes** | Workflow 层出现 |
| **Expected Git Diff** | `workflow/node.py`、`workflow/edge.py` |
| **Quality Gate** | 线性 Workflow 可执行；文档同步 |

---

## Phase12 — State Machine Upgrade

| 项 | 内容 |
|----|------|
| **Goal** | Interrupt、Resume |
| **Deliverables** | WorkflowEngine interrupt/resume；WaitingApproval 完善 |
| **Learning Focus** | 长运行 Workflow；Human-in-the-Loop |
| **Architecture Changes** | Runtime 状态机扩展 |
| **Expected Git Diff** | `workflow/engine.py`；状态机更新 |
| **Quality Gate** | Workflow 可回放；Interrupt/Resume 可测 |

---

## Phase13 — Parallel Execution

| 项 | 内容 |
|----|------|
| **Goal** | Parallel Tool、Branch、Merge |
| **Deliverables** | 并行 Tool 执行；条件 Branch |
| **Learning Focus** | 并发与合并策略 |
| **Architecture Changes** | Execution 层并行 |
| **Expected Git Diff** | `workflow/parallel.py`；并行测试 |
| **Quality Gate** | Parallel Tool 结果可合并；无竞态 |

---

# V4 Production Agent

## Phase14 — MCP Integration

| 项 | 内容 |
|----|------|
| **Goal** | MCP Client、Tool Discovery |
| **Deliverables** | `MCPClient`；Tool Registry 与 MCP 整合 |
| **Learning Focus** | MCP 协议；外部 Tool 发现 |
| **Architecture Changes** | integrations/mcp；Tools 层扩展 |
| **Expected Git Diff** | `integrations/mcp/`；MCP 契约测试 |
| **Quality Gate** | MCP 接口稳定；Tool Discovery 可测 |

---

## Phase15 — Production Hardening

| 项 | 内容 |
|----|------|
| **Goal** | Logging、Tracing、Metrics、Config |
| **Deliverables** | 结构化日志；OpenTelemetry（可选）；Metrics；配置系统 |
| **Learning Focus** | 生产可观测性 |
| **Architecture Changes** | Infrastructure 完善 |
| **Expected Git Diff** | `jarvis/config.py`；logging/tracing 中间件 |
| **Quality Gate** | 关键路径有 Trace；Config 可环境变量覆盖 |

---

## 当前进度

| 版本 | Phase | 状态 |
|------|-------|------|
| V0 | Phase0 Design Gate | ✅ 完成 |
| V0 | Phase1 Project Skeleton | ✅ 完成 |
| V0 | Phase2 Dev Infrastructure | ✅ 完成 |
| V0 | Phase3 Runtime Foundation | ✅ 完成 |
| V1 | Phase4 LLM Adapter | 🔄 下一 Phase |
| V1 | Phase5–7 | ⏳ 待开始 |
| V2 | Phase8–10 | ⏳ 待开始 |
| V3 | Phase11–13 | ⏳ 待开始 |
| V4 | Phase14–15 | ⏳ 待开始 |

---

## 文档更新要求

每个 Phase 完成后更新：

- [Roadmap](./07-roadmap.md)（本文件）
- [Architecture](./02-architecture.md)
- [Domain Model](./03-domain-model.md)
- [Runtime State Machine](./04-runtime-state-machine.md)（如适用）
- [Interface Spec](./09-interface-spec.md)（如适用）
- [ADR](./adr/)（如有架构变更）

见 [Quality Gates](./10-quality-gates.md)。
