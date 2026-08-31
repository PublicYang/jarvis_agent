# Project Structure

> Jarvis 最终目录规划，Phase0 仅规划不创建业务目录。  
> 相关文档：[Roadmap](./07-roadmap.md) · [Tech Stack](./06-tech-stack.md) · [Interface Spec](./09-interface-spec.md)

---

## 目录树

```text
jarvis_agent/
├── docs/                    # 设计文档、ADR
│   └── adr/
├── runtime/                 # Runtime 引擎
├── planner/                 # Planner
├── tools/                   # Tool 注册与执行
├── llm/                     # LLM Adapter
├── memory/                  # Memory
├── workflow/                # Workflow 引擎
├── integrations/            # 接入层（CLI/Web/BAG 等）
├── tests/                   # 测试
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## 目录与 Phase 对应

| 目录 | Phase | 职责 |
|------|-------|------|
| docs/ | Phase0 | 设计文档 |
| integrations/ | Phase1 | CLI 骨架；后续 Web/BAG |
| runtime/ | Phase3 | Message、State、Task |
| llm/ | Phase4 | LLM Adapter |
| planner/ | Phase5 | Planner |
| tools/ | Phase6 | ToolCall、Observation |
| memory/ | Phase8–10 | Memory、Context、Persistence |
| workflow/ | Phase11–13 | Node、Edge、Parallel |
| integrations/ (MCP) | Phase14 | MCP Client 适配 |
| tests/ | Phase2 起 | 全阶段测试 |

---

## 各目录预期结构

### runtime/

```text
runtime/
├── __init__.py
├── models.py          # Message, State, Task (Phase3)
├── engine.py          # 主循环 (Phase7)
└── state_machine.py   # 状态机 (Phase7)
```

### planner/

```text
planner/
├── __init__.py
├── base.py            # Planner 接口 (Phase5)
└── simple.py          # 首版实现 (Phase5)
```

### tools/

```text
tools/
├── __init__.py
├── base.py            # Tool 接口 (Phase6)
├── registry.py        # 注册表 (Phase6)
└── executor.py        # 执行器 (Phase6)
```

### llm/

```text
llm/
├── __init__.py
├── adapter.py         # LLM Adapter 接口 (Phase4)
└── openai_compat.py   # 实现 (Phase4)
```

### memory/

```text
memory/
├── __init__.py
├── store.py           # Memory 接口 (Phase8)
├── context.py         # Context Builder (Phase9)
└── sqlite.py          # SQLite 持久化 (Phase10)
```

### workflow/

```text
workflow/
├── __init__.py
├── node.py            # Node (Phase11)
├── edge.py            # Edge (Phase11)
├── engine.py          # Workflow 引擎 (Phase12)
└── parallel.py        # Parallel/Branch (Phase13)
```

### integrations/

```text
integrations/
├── __init__.py
├── cli/               # Typer CLI (Phase1)
├── web/               # HTTP API (未来)
├── bag/               # BAG 适配 (未来)
└── mcp/               # MCP 集成 (Phase14)
```

### tests/

```text
tests/
├── conftest.py
├── runtime/
├── planner/
├── tools/
├── memory/
└── workflow/
```

---

## Phase0 已创建

| 路径 | 说明 |
|------|------|
| docs/ | 全部 Master Plan 文档 |
| docs/adr/ | ADR-001 ~ ADR-003 |
| README.md | 项目说明 |
| .gitignore | Git 忽略 |
| pyproject.toml | 基础配置 |

## Phase0 禁止创建

- runtime/、planner/、tools/、llm/、memory/、workflow/ 业务代码
- integrations/ 实现代码（Phase1 起）

---

## 包命名

顶层包名：`jarvis`（Phase1 确定并在 pyproject.toml 配置）。
