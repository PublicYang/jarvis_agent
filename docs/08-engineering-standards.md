# Engineering Standards

> Jarvis 工程规范。  
> 相关文档：[Tech Stack](./06-tech-stack.md) · [Development Principles](./12-development-principles.md) · [Quality Gates](./10-quality-gates.md)

---

## Code Style

### Ruff

- Linter：替代 Flake8、isort
- 配置：`pyproject.toml` → `[tool.ruff]`
- 命令：`uv run ruff check .`

### Black

- 行宽：88
- 命令：`uv run black .`

### Type Hints

- 公开 API 必须有类型注解
- Domain 对象使用 Pydantic v2 Model
- 接口使用 `Protocol`（见 [Interface Spec](./09-interface-spec.md)）

---

## Commit

[Conventional Commits](https://www.conventionalcommits.org/)：

```text
<type>(<scope>): <description>
```

| Type | 用途 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档 |
| refactor | 重构 |
| test | 测试 |
| chore | 工具/构建 |

| Scope | 模块 |
|-------|------|
| runtime | runtime/ |
| planner | planner/ |
| tools | tools/ |
| memory | memory/ |
| workflow | workflow/ |
| llm | llm/ |
| integrations | integrations/ |
| docs | docs/ |

示例：

```text
feat(runtime): add State model with status enum
docs(roadmap): mark Phase3 complete
test(tools): add tool registry tests
```

---

## Branch

简单 Git Flow：

```text
main
  ├── feature/phase3-runtime-models
  ├── feature/phase6-tool-calling
  └── ...
```

- 每个 Phase 独立 feature 分支
- 合并前通过 Quality Gate
- 禁止 force push main

---

## pre-commit（Phase2 起）

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff
      - id: black
      - id: pytest
```

---

## 测试

- 框架：pytest
- 结构：`tests/` 镜像源码目录
- 命名：`test_*.py`
- 每个 Phase 必须有对应测试才能通过 Gate

---

## 文档

- 设计文档：`docs/`
- ADR：`docs/adr/`
- 文档间互相引用
- Phase 完成 → 同步更新相关文档

---

## 禁止

- 跳过 Quality Gate 合并
- 一次 commit 整个 Phase 代码
- 未更新 ADR 的 breaking 接口变更
