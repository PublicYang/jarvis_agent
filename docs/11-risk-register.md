# Risk Register

> Jarvis 项目风险登记与缓解措施。  
> 相关文档：[ADR-001](./adr/ADR-001-runtime-self-build.md) · [ADR-003](./adr/ADR-003-framework-introduction-strategy.md) · [Development Principles](./12-development-principles.md)

---

## 风险清单

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Runtime 复杂度膨胀 | 高 | 分层架构 ADR；一 Phase 一能力；Quality Gate 强制 Diff Review |
| Tool 耦合 | 中 | Tool 接口抽象；Registry 模式；Execution 层隔离 |
| Memory 污染 | 中 | State/Memory 职责分离；MemoryRecord scope 隔离 |
| Context 无限增长 | 高 | Phase9 Context Builder；Token 预算；压缩策略 |
| Framework 替代风险 | 中 | ADR-003 约束；后期对比引入；禁止前期依赖 |

---

## Runtime 复杂度膨胀

**风险**：自研 Runtime 随 Phase 增加，代码膨胀，最终与 LangGraph 等价但质量更低。

**影响**：

- 维护成本上升
- 学习曲线变陡
- 偏离「可观察演进」目标

**缓解措施**：

- [ADR-002 分层架构](./adr/ADR-002-layered-architecture.md) 约束职责
- [Development Principles — 一个 Phase 一个能力](./12-development-principles.md)
- 每 Phase Expected Git Diff 限制变更范围
- Phase7 完成后评估复杂度，必要时重构 + ADR

---

## Tool 耦合

**风险**：Tool 直接依赖 Runtime 内部对象；或 Runtime 硬编码 Tool 逻辑。

**影响**：

- 新 Tool 难以添加
- 测试困难
- MCP 集成（Phase14）受阻

**缓解措施**：

- [Interface Spec — Tool](./09-interface-spec.md) 契约
- ToolRegistry 统一注册与执行
- ToolCall/Observation 作为唯一数据通道

---

## Memory 污染

**风险**：State 与 Memory 职责重叠；跨 Session 数据泄漏；Memory 写入无 scope。

**影响**：

- 数据不一致
- 隐私/安全问题
- Planner 收到错误 Context

**缓解措施**：

- State = 运行时上下文；Memory = 跨 run 持久化
- MemoryRecord.scope：`session` / `user` / `global`
- Phase8 Gate：读写一致性测试

---

## Context 无限增长

**风险**：Message/Observation 无限追加，超出 LLM Token 窗口。

**影响**：

- LLM 调用失败或成本激增
- Planner 决策质量下降

**缓解措施**：

- Phase9 Context Builder + 压缩策略
- Token 预算硬限制
- 重要消息标记保留
- Quality Gate：压缩后 Planner 仍可决策

---

## Framework 替代风险

**风险**：开发中途引入 LangGraph 等框架，或自研 Runtime 越写越像框架。

**影响**：

- 学习目标偏离
- 重复造轮子且无框架质量

**缓解措施**：

- [ADR-001 自研决策](./adr/ADR-001-runtime-self-build.md)
- [ADR-003 后期引入策略](./adr/ADR-003-framework-introduction-strategy.md)
- 禁止 Phase7 前引入框架依赖
- V4 后可做对比实验分支

---

## 风险审查节奏

| 时机 | 动作 |
|------|------|
| 每 Phase 开始前 | 回顾本 Register |
| 每 Phase 结束后 | 更新缓解效果 |
| V1 结束（Phase7） | 全面审查；决定是否重构 |

---

## 新增风险流程

1. 登记本文档
2. 如需架构决策 → 新增 ADR
3. 在 Roadmap / Quality Gates 体现应对
