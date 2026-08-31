# Tech Stack

> Jarvis 技术选型及原因。  
> 相关文档：[Engineering Standards](./08-engineering-standards.md) · [ADR-001](./adr/ADR-001-runtime-self-build.md) · [ADR-003](./adr/ADR-003-framework-introduction-strategy.md)

---

## 选型表

| 技术 | 原因 |
|------|------|
| **Python 3.12** | Agent 生态主流；类型提示与 async 成熟 |
| **Pydantic v2** | Domain 对象校验；Message/State 等强类型 |
| **Typer** | CLI Integration；类型友好 |
| **httpx** | LLM API、Tool 外部调用；同步/异步 |
| **uv** | 快速包管理；锁文件可复现 |
| **pytest** | 测试标准；Quality Gate 依赖 |
| **Ruff** | 极速 Lint；替代 Flake8 + isort |
| **Black** | 统一格式化 |
| **pre-commit** | Git 提交前自动 Lint/Format（Phase2） |
| **SQLite** | Memory 持久化（Phase10）；零依赖 |

---

## 前期不引入

| 框架 | 原因 |
|------|------|
| **LangGraph** | 先自己实现 Runtime，理解底层机制 |
| **CrewAI** | 多 Agent 非当前目标 |
| **AutoGen** | 易与自研路径混淆 |

策略详见 [ADR-003 Framework Introduction Strategy](./adr/ADR-003-framework-introduction-strategy.md)。

---

## Phase 依赖引入计划

| Phase | 新增依赖 |
|-------|----------|
| Phase2 | pytest, ruff, black, pre-commit |
| Phase3 | pydantic |
| Phase4 | httpx |
| Phase1/4 | typer |
| Phase10 | sqlite3（标准库） |

---

## 开发命令（Phase2 起）

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run black .
pre-commit run --all-files
```

---

## 未来可能引入

| 技术 | 场景 | 决策 |
|------|------|------|
| LangGraph | V4 后对比学习 | ADR-003 |
| OpenTelemetry | Phase15 Tracing | Phase15 ADR |
| Redis | 分布式 Memory | 按需 ADR |
