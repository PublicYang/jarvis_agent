# Quality Gates

> 全项目质量闸门，每个 Phase 必须满足。  
> 相关文档：[Roadmap](./07-roadmap.md) · [Engineering Standards](./08-engineering-standards.md)

---

## 通用 Gate（每个 Phase）

| 检查项 | 要求 |
|--------|------|
| **文档同步** | Roadmap、Architecture、Domain Model 更新 |
| **测试通过** | `uv run pytest` 全绿（Phase2 起） |
| **Lint 通过** | `ruff check` + `black --check`（Phase2 起） |
| **ADR 更新** | 架构变更必须有 ADR |
| **Roadmap 更新** | 标记 Phase 完成、记录经验 |
| **Interface Spec** | 接口变更同步 [Interface Spec](./09-interface-spec.md) |
| **Git Diff Review** | Expected Git Diff 与实际一致 |

---

## V0 Foundation

| Phase | Gate |
|-------|------|
| **Phase0** | Master Plan Checklist 全 ✅；文档交叉引用完整 |
| **Phase1** | `uv sync` 成功；目录结构与 Project Structure 一致 |
| **Phase2** | pytest/ruff/black/pre-commit 全绿 |
| **Phase3** | Message/State/Task 模型测试通过；不调用 LLM |

---

## V1 Core Runtime

| Phase | Gate |
|-------|------|
| **Phase4** | LLM Adapter mock 测试通过；Interface Spec 一致 |
| **Phase5** | PlannerOutput 校验；Planning 状态可测 |
| **Phase6** | Agent 闭环集成测试；ToolCall 可追踪 |
| **Phase7** | 状态机与文档同步；CLI 单次对话可用；Retry/Timeout/Cancel 可测 |

---

## V2 Stateful Agent

| Phase | Gate |
|-------|------|
| **Phase8** | Memory 读写一致 |
| **Phase9** | Context 压缩后 Planner 可决策 |
| **Phase10** | SQLite 持久化；重启可恢复 |

---

## V3 Workflow Engine

| Phase | Gate |
|-------|------|
| **Phase11** | 线性 Workflow 可执行 |
| **Phase12** | Workflow 可回放；Interrupt/Resume 可测 |
| **Phase13** | Parallel Tool 无竞态；Branch 可验证 |

---

## V4 Production Agent

| Phase | Gate |
|-------|------|
| **Phase14** | MCP 契约测试；Tool Discovery 可测 |
| **Phase15** | Logging/Tracing/Metrics 关键路径覆盖；Config 可配置 |

---

## Phase 完成 Checklist 模板

```markdown
## Phase N Gate Checklist

- [ ] Goal 达成
- [ ] Deliverables 交付
- [ ] Expected Git Diff 已 Review
- [ ] pytest 全绿
- [ ] ruff + black 通过
- [ ] Roadmap 已更新
- [ ] Architecture 已更新
- [ ] Domain Model 已更新（如适用）
- [ ] Interface Spec 已更新（如适用）
- [ ] ADR 已更新（如适用）
- [ ] 无已知 Blocker
```

---

## 文档同步矩阵

| Phase | 必更新文档 |
|-------|-----------|
| Phase3+ | Domain Model |
| Phase4+ | Interface Spec (LLM) |
| Phase5+ | Runtime State Machine |
| Phase6+ | Architecture (Execution/Tools) |
| Phase8+ | Domain Model (MemoryRecord) |
| Phase11+ | Architecture (Workflow) |
| 任意架构变更 | ADR |
