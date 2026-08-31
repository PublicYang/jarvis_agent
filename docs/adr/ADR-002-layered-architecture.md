# ADR-002: 分层架构

- **状态**：已接受
- **日期**：2026-08-31
- **相关**：[Architecture](../02-architecture.md) · [Interface Spec](../09-interface-spec.md)

---

## 背景

Agent 系统涉及 LLM 调用、规划、工具执行、记忆、工作流、接入等多维能力。  
若无清晰分层，易出现：

- Runtime 与 Tool 耦合
- Integration 逻辑渗入核心
- 难以独立测试与演进

---

## 决策

**采用七层分层架构**：

```text
Application → Runtime → Planning → Execution → Tools → LLM Adapter → Infrastructure
```

**规则**：

1. 上层依赖下层，下层不感知上层
2. Runtime 是唯一 orchestrator
3. Integration（CLI/Web/BAG）仅依赖 Application
4. 跨层通过 Domain Model + Interface Spec 通信

---

## 影响

**正面**：

- 职责清晰，Phase 可逐层引入
- Tool/Planner 可独立测试
- BAG 等接入方与核心解耦

**负面**：

- 初期分层可能显得「过重」
- 需要维护 Interface Spec

**缓解**：Phase3 起仅 Runtime 层有代码；随 Phase 渐进填充。

---

## 未来可能改变

| 条件 | 决策 |
|------|------|
| Workflow 层与 Runtime 边界模糊 | 合并或拆分，新 ADR |
| MCP 成为 Tool 主要来源 | Tools 层扩展，Architecture 更新 |
| 性能瓶颈 | 允许层间 shortcut（需 ADR + _benchmark） |
