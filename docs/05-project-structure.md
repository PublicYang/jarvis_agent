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
├── loop.py            # 最小闭环 (Phase6)
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
├── base.py            # Tool 接口、ToolCall、Observation (Phase6)
├── registry.py        # 注册表 (Phase6)
├── executor.py        # 执行器 (Phase6)
└── echo.py            # 示例 Tool (Phase6)
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

## Phase1 已创建

| 路径 | 说明 |
|------|------|
| runtime/ | 空包（Phase3 起加 models） |
| planner/ | 空包（Phase5 起加接口） |
| tools/ | 空包（Phase6 起加 Tool） |
| llm/ | 空包（Phase4 起加 Adapter） |
| memory/ | 空包（Phase8 起加 Store） |
| workflow/ | 空包（Phase11 起加 Node/Edge） |
| integrations/ | 接入层空包 |
| integrations/cli/ | CLI 占位（Phase7 实现） |

## Phase2 已创建

| 路径 | 说明 |
|------|------|
| tests/conftest.py | pytest 共享 fixture |
| tests/test_placeholder.py | 占位测试，验证工具链 |
| .pre-commit-config.yaml | ruff + black + pytest hooks |

## Phase3 已创建

| 路径 | 说明 |
|------|------|
| runtime/models.py | Message、State、Task Pydantic 模型 |
| tests/runtime/test_models.py | 模型单元测试 |

## Phase4 已创建

| 路径 | 说明 |
|------|------|
| llm/adapter.py | `LLMAdapter` Protocol、`LLMRequest`/`LLMResponse` |
| llm/openai_compat.py | OpenAI 兼容实现（httpx） |
| tests/llm/test_openai_compat.py | mock HTTP 测试 |

## Phase5 已创建

| 路径 | 说明 |
|------|------|
| planner/base.py | `Planner` Protocol、`PlannerOutput`、`DecisionType` |
| planner/simple.py | `SimplePlanner`（LLM 驱动 reply/clarify） |
| tests/planner/test_simple.py | Planner 单元测试 |

## Phase6 已创建

| 路径 | 说明 |
|------|------|
| tools/base.py | `Tool` Protocol、`ToolCall`、`Observation` |
| tools/registry.py | `InMemoryToolRegistry` |
| tools/executor.py | `ToolExecutor`（pending → running → completed/failed） |
| tools/echo.py | 示例 `EchoTool` |
| runtime/loop.py | 最小闭环：Planning → Tool → Planning → Reply |
| tests/tools/test_registry.py | Registry / Executor 单元测试 |
| tests/runtime/test_loop.py | 闭环集成测试 |

## Phase7 已创建

| 路径 | 说明 |
|------|------|
| runtime/state_machine.py | `RuntimePhase` 与合法转移 |
| runtime/engine.py | `RuntimeEngine`（Retry/Timeout/Cancel/Approval） |
| integrations/cli/app.py | Typer CLI 组合根：`jarvis chat` |
| tests/runtime/test_state_machine.py | 状态机单元测试 |
| tests/runtime/test_engine.py | Engine 边界条件测试 |
| tests/integrations/test_cli.py | CLI 单次对话测试 |

## Phase0 禁止创建

- 跨 Phase 提前实现业务能力（历史约束；Phase1+ 已按 Roadmap 落地）

---

## 包命名

| 项 | 值 |
|----|-----|
| **发行名** | `jarvis-agent`（pyproject `[project].name`） |
| **导入包** | 扁平布局：`runtime`、`planner`、`tools`、`llm`、`memory`、`workflow`、`integrations` |
| **CLI 入口** | `jarvis = "integrations.cli:app"` → `jarvis chat` |
