# ADR-003: 框架引入策略

- **状态**：已接受
- **日期**：2026-08-31
- **相关**：[Tech Stack](../06-tech-stack.md) · [ADR-001](./ADR-001-runtime-self-build.md) · [Risk Register](../11-risk-register.md)

---

## 背景

LangGraph、CrewAI、AutoGen 等框架封装了 Runtime、Planner、Workflow 能力。  
Jarvis 选择自研（ADR-001），但完全拒绝框架可能错过行业最佳实践对比学习。

---

## 决策

**前期（Phase0–Phase7）不引入 LangGraph、CrewAI、AutoGen。**

**后期（V4 完成后）可按需引入，仅用于**：

1. **对比学习**：与自研 Runtime 行为对比
2. **参考实现**：Workflow 复杂场景参考 LangGraph
3. **实验分支**：非 main 分支，不影响自研主线

**禁止**：

- 用框架替代 Phase3–Phase7 的自研实现
- 在 main 分支直接依赖框架作为核心 Runtime

---

## 影响

**正面**：

- Phase0–7 学习路径不被框架干扰
- 后期可理性评估框架价值
- 降低 Framework 替代风险

**负面**：

- 无法利用框架加速 V1
- 后期对比需额外投入

---

## 未来可能改变

| 条件 | 决策 |
|------|------|
| 自研 Workflow 过于复杂 | 评估 LangGraph 作为 Workflow 后端（新 ADR） |
| 行业 MCP 标准成熟 | 可能引入官方 MCP SDK（非 Agent 框架） |
| 团队转向生产交付 | fork `framework-integration` 分支 |
