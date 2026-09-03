# Architecture

> Jarvis 分层架构与 Runtime 数据流。  
> 相关文档：[Domain Model](./03-domain-model.md) · [Runtime State Machine](./04-runtime-state-machine.md) · [ADR-002 Layered Architecture](./adr/ADR-002-layered-architecture.md)

---

## 分层架构

```text
Application
    │
Runtime
    │
Planning
    │
Execution
    │
Tools
    │
LLM Adapter
    │
Infrastructure
```

### 各层职责

| 层 | 职责 | 引入 Phase |
|----|------|------------|
| **Application** | 对外 Agent API；Integration 入口（CLI/Web 等） | Phase1 |
| **Runtime** | 主循环、状态机、State 生命周期 | Phase3 |
| **Planning** | 任务分解、Decision 生成 | Phase5 |
| **Execution** | 执行 Decision（Tool 或 Reply） | Phase6 |
| **Tools** | Tool 注册、调用、Observation 封装 | Phase6 |
| **LLM Adapter** | 模型 API 抽象 | Phase4 |
| **Infrastructure** | 配置、日志、持久化、Tracing | Phase2/10/15 |

### 依赖规则

- 上层依赖下层；下层不感知上层
- Runtime 是唯一 orchestrator
- 跨层数据传递使用 [Domain Model](./03-domain-model.md) 对象
- Integration 仅依赖 Application 层

---

## 系统定位（与 Client 关系）

```text
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│   CLI    │  │   Web    │  │ Telegram │  │   BAG    │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │
     └─────────────┴──────┬──────┴─────────────┘
                          │ Integration Protocol
                          ▼
              ┌───────────────────────┐
              │   Application Layer   │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │      Runtime Layer      │
              └───────────────────────┘
```

BAG 仅为 Integration 之一，不是 Jarvis 父项目。见 [Project Charter](./00-project-charter.md)。

---

## Runtime 数据流

```text
User
 ↓
Planner
 ↓
Decision
 ↓
Tool
 ↓
Observation
 ↓
State
 ↓
Loop
 ↓
Answer
```

### 逐步解释

#### 1. User

Client 通过 Integration 发送用户输入，转换为 `Message` 对象进入 Runtime。

#### 2. Planner

Runtime 进入 `Planning` 状态，Planner 分析 State 与 Task，输出 `PlannerOutput`。见 [Interface Spec — Planner](./09-interface-spec.md#planner)。

#### 3. Decision

PlannerOutput 解析为 Decision：

| 类型 | 动作 |
|------|------|
| `reply` | 生成 Answer，结束 Loop |
| `tool_call` | 进入 Executing |
| `clarify` | 请求用户澄清（可选） |

#### 4. Tool

Execution 层构造 `ToolCall`，调用 Tool Registry 中对应工具。Runtime 进入 `WaitingTool`。

#### 5. Observation

Tool 返回 `Observation`（success、content、error），写入 State。

#### 6. State

State 聚合 messages、task、tool_calls、observations、planner_outputs。每次 Loop 迭代更新。见 [Domain Model — State](./03-domain-model.md#state)。

#### 7. Loop

主循环：Planning → Executing → WaitingTool → Planning，直到 Reply 或终止。

Phase6 实现为 `runtime/loop.py` 的同步最小闭环（Tool 立即返回 Observation）。完整状态机（Retry/Timeout/Cancel）见 Phase7。见 [Runtime State Machine](./04-runtime-state-machine.md)。

#### 8. Answer

Runtime 进入 `Completed`，Application 层封装 Answer 返回 Client。

---

## 架构演进矩阵

| Phase | 架构变化 |
|-------|----------|
| Phase3 | 引入 Runtime 层；Message、State、Task |
| Phase4 | 引入 LLM Adapter 层 |
| Phase5 | 引入 Planning 层 |
| Phase6 | 引入 Execution + Tools 层；`runtime/loop.py` 最小闭环 |
| Phase7 | Runtime 完整状态机 + `RuntimeEngine`；CLI 组合根 |
| Phase8–10 | Memory 扩展 State；Infrastructure 持久化 |
| Phase11–13 | Workflow 编排层（Node/Edge） |
| Phase14 | MCP 与 Tools 层整合 |
| Phase15 | Infrastructure 完善（Logging/Tracing/Metrics） |

每 Phase 完成后更新本文档。见 [Quality Gates](./10-quality-gates.md)。

---

## 与 Interface Spec 的关系

各层公开接口定义见 [Interface Spec](./09-interface-spec.md)，实现不得违反接口契约。
