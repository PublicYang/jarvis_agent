# ADR-001: Runtime 自研

- **状态**：已接受
- **日期**：2026-08-31
- **相关**：[Tech Stack](../06-tech-stack.md) · [PRD](../01-product-requirements.md) · [Risk Register](../11-risk-register.md)

---

## 背景

Agent 生态有 LangGraph、CrewAI、AutoGen 等成熟框架，可快速搭建 Agent。  
Jarvis 目标是**学习生产级 Runtime 演进**，而非最快交付 Demo。

---

## 决策

**采用自研 Runtime**，Phase0–Phase7 不引入上述框架作为核心依赖。

按 Phase 自研：数据结构 → LLM Adapter → Planner → Tool → Loop → Memory → Workflow → MCP。

---

## 影响

**正面**：

- 每 Phase 学习目标清晰
- 架构可控，Diff 可观察
- 任何 Client 可接入，不受框架约束

**负面**：

- 开发周期更长
- 需自行处理 Retry、Timeout 等
- 可能重复造轮子

**缓解**：[ADR-003](./ADR-003-framework-introduction-strategy.md) 定义后期引入策略；[Risk Register](../11-risk-register.md) 约束复杂度。

---

## 未来可能改变

| 条件 | 决策 |
|------|------|
| V1 完成，学习目标达成 | 可选 LangGraph 对比分支 |
| 特定模块成本过高 | 单模块改用框架（新 ADR） |
| 生产交付压力 | fork 分支，main 保持自研 |
