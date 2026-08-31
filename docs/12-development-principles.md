# Development Principles

> Jarvis 全项目开发纪律。  
> 相关文档：[Engineering Standards](./08-engineering-standards.md) · [Quality Gates](./10-quality-gates.md) · [Roadmap](./07-roadmap.md)

---

## 小步提交

- 每个 commit 对应一个可验证增量
- 示例：`feat(runtime): add Message model` → `feat(runtime): add State status enum`
- 禁止一次 commit 整个 Phase

---

## 一个 Phase 一个能力

- 严格按 [Roadmap](./07-roadmap.md) Phase 顺序推进
- 不跨 Phase 提前实现（如 Phase3 不调用 LLM）
- Phase 内也拆分小步：模型 → 测试 → 集成

---

## 每次必须 Review Git Diff

每次提交前：

1. **查看 Git Diff**：变更范围符合 Expected Git Diff（见 Roadmap 各 Phase）
2. **查看新增文件**：目录符合 [Project Structure](./05-project-structure.md)
3. **查看职责变化**：不违反分层（Tool 不依赖 Planner 内部）

---

## 不允许一次生成整个项目

- 禁止 AI/开发者一次输出全部模块
- 禁止跳过 Phase 直接实现 V4 能力
- Phase0 仅文档；Phase1 仅骨架

---

## 可以重构，但必须更新 ADR

- 学习优先，允许回退重写
- 重构若改变架构 → 新增或更新 ADR
- 重构后同步 Architecture、Domain Model、Interface Spec

---

## 文档驱动

- **唯一依据**：`docs/` 目录
- 代码不得偏离 Interface Spec
- Phase 完成 → 文档先于 merge 更新

---

## 可观察演进

- 每个 Phase 的 Expected Git Diff 可预测
- PR/Commit 可映射到 Roadmap Phase
- 架构变化记录在 Architecture 演进矩阵

---

## 学习优先

- 不追求 Demo 速度
- 不追求代码行数
- 追求理解 Runtime 如何成长

---

## 当前阶段

**Phase0 Design Gate**：仅产出 Master Plan 文档，不写业务代码。  
评审通过后进入 **Phase1 Project Skeleton**。
