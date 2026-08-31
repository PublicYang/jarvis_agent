# Runtime State Machine

> Jarvis Runtime 完整状态机设计。  
> 相关文档：[Architecture](./02-architecture.md) · [Domain Model — State](./03-domain-model.md#state) · [Interface Spec](./09-interface-spec.md)

---

## 主状态流

```text
Idle
 ↓
Planning
 ↓
Executing
 ↓
WaitingTool
 ↓
Planning
 ↓
Completed
```

---

## 状态说明

| 状态 | 职责 | 进入 | 退出 |
|------|------|------|------|
| **Idle** | 等待请求 | 初始化 / 上一 run 结束 | 收到 User 请求 |
| **Planning** | 调用 Planner | Idle / WaitingTool 收到 Observation | Decision 确定 |
| **Executing** | 执行 Decision | Planning 输出 tool_call 或 reply | Tool 发起 / Reply 生成 |
| **WaitingTool** | 等待 Tool | Executing 发起 ToolCall | Observation 返回 |
| **Completed** | 结束 | Executing 生成 Reply | — |

---

## 完整状态图

```text
                    ┌─────────┐
                    │  Idle   │
                    └────┬────┘
                         │ Request
                         ▼
                    ┌─────────┐
         ┌──────────│Planning │◄──────────────────┐
         │          └────┬────┘                   │
         │               │                         │
         │     ┌─────────┼─────────┐               │
         │     ▼         ▼         ▼               │
         │  Reply    ToolCall   Clarify           │
         │     │         │         │               │
         │     │         ▼         │               │
         │     │   ┌───────────┐   │               │
         │     │   │ Executing │   │               │
         │     │   └─────┬─────┘   │               │
         │     │         ▼         │               │
         │     │   ┌─────────────┐ │               │
         │     │   │ WaitingTool │─┘               │
         │     │   └──────┬──────┘                 │
         │     │          │ Observation            │
         │     ▼          └────────────────────────┘
         │  ┌───────────┐
         └──│ Completed │
            └───────────┘
```

---

## Retry

**为什么存在**：Tool 失败、LLM 超时、Planner 输出格式错误时，有限重试避免偶发错误终止整个 run。

```text
Executing ──(fail, retry < max)──→ Planning
WaitingTool ──(timeout, retry)──→ Executing
Planning ──(invalid output)──→ Planning
```

| 参数 | 建议 |
|------|------|
| max_retries | 3 |
| backoff | 指数退避 |

**引入 Phase**：Phase7

---

## Timeout

**为什么存在**：避免 Runtime 永久阻塞。

```text
Planning ──(LLM timeout)──→ Failed
WaitingTool ──(Tool timeout)──→ Failed
任意 ──(run timeout)──→ Failed
```

| 参数 | 建议 |
|------|------|
| llm_timeout | 60s |
| tool_timeout | 30s |
| run_timeout | 300s |

**引入 Phase**：Phase7

---

## Cancel

**为什么存在**：Client 或用户主动取消，优雅释放资源。

```text
Planning / Executing / WaitingTool ──(Cancel)──→ Cancelled
```

**引入 Phase**：Phase7

---

## Approval

**为什么存在**：敏感 Tool（写文件、发消息）需 Human-in-the-Loop 确认。

```text
Planning ──(tool_call, requires_approval)──→ WaitingApproval
WaitingApproval ──(Approved)──→ Executing
WaitingApproval ──(Rejected)──→ Planning
WaitingApproval ──(Timeout)──→ Cancelled
```

**引入 Phase**：Phase7（基础）→ Phase12（Workflow Interrupt/Resume 完善）

---

## 终止状态

| 状态 | State.status |
|------|--------------|
| Completed | Completed |
| Failed | Failed |
| Cancelled | Cancelled |

---

## State 与 Runtime 状态映射

| Runtime | State.status |
|---------|--------------|
| Idle | — |
| Planning, Executing | Running |
| WaitingTool | WaitingTool |
| WaitingApproval | Running |
| Completed | Completed |
| Failed | Failed |
| Cancelled | Cancelled |

---

## Phase 引入计划

| 能力 | Phase |
|------|-------|
| Idle → Planning → Executing → Completed | Phase7 |
| WaitingTool 循环 | Phase6 |
| Retry, Timeout, Cancel, Approval | Phase7 |
| Interrupt, Resume | Phase12 |
| Parallel Tool | Phase13 |
