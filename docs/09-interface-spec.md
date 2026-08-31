# Interface Spec

> Jarvis 核心接口规范，仅签名不写实现。  
> 相关文档：[Architecture](./02-architecture.md) · [Domain Model](./03-domain-model.md)

---

## 约定

- 语言：Python 类型注解风格
- 所有接口为抽象契约，实现不得改变语义
- Domain 对象见 [Domain Model](./03-domain-model.md)

---

## LLM Adapter

```python
# llm/adapter.py

class LLMRequest(TypedDict):
    messages: list[Message]
    model: str
    temperature: float
    max_tokens: int | None

class LLMResponse(TypedDict):
    content: str
    finish_reason: str
    usage: dict[str, int]

class LLMAdapter(Protocol):
    """Phase4 引入。"""

    def complete(self, request: LLMRequest) -> LLMResponse:
        """同步完成一次 LLM 调用。"""
        ...

    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        """异步完成一次 LLM 调用。"""
        ...
```

---

## Planner

```python
# planner/base.py

class Planner(Protocol):
    """Phase5 引入。"""

    def plan(self, state: State) -> PlannerOutput:
        """
        根据当前 State 生成下一步 Decision。
        不得修改 State，仅读取。
        """
        ...
```

---

## Tool

```python
# tools/base.py

class ToolDefinition(TypedDict):
    name: str
    description: str
    parameters: dict  # JSON Schema

class Tool(Protocol):
    """Phase6 引入。"""

    @property
    def definition(self) -> ToolDefinition:
        """返回 Tool 元数据，供 Planner/LLM 使用。"""
        ...

    def execute(self, arguments: dict) -> Observation:
        """执行 Tool，返回 Observation。"""
        ...

    async def aexecute(self, arguments: dict) -> Observation:
        """异步执行。"""
        ...
```

---

## Tool Registry

```python
# tools/registry.py

class ToolRegistry(Protocol):
    """Phase6 引入。"""

    def register(self, tool: Tool) -> None: ...

    def get(self, name: str) -> Tool: ...

    def list_tools(self) -> list[ToolDefinition]: ...

    def execute(self, tool_call: ToolCall) -> Observation: ...
```

---

## Memory

```python
# memory/store.py

class MemoryStore(Protocol):
    """Phase8 引入。"""

    def write(self, record: MemoryRecord) -> None: ...

    def read(self, key: str, scope: MemoryScope) -> MemoryRecord | None: ...

    def search(self, query: str, limit: int) -> list[MemoryRecord]: ...

    def delete(self, record_id: str) -> None: ...
```

---

## Context Builder

```python
# memory/context.py

class ContextBuilder(Protocol):
    """Phase9 引入。"""

    def build(self, state: State, memory: MemoryStore) -> list[Message]:
        """
        从 State + Memory 构建 LLM Context。
        负责压缩与 Token 预算。
        """
        ...
```

---

## Runtime Engine

```python
# runtime/engine.py

class RuntimeEngine(Protocol):
    """Phase7 引入完整 Loop。"""

    def run(self, user_message: Message) -> State:
        """执行一次完整 Agent Run，返回终态 State。"""
        ...

    def cancel(self, state_id: str) -> None:
        """取消运行中的 State。"""
        ...
```

---

## Application / Agent API

```python
# integrations 层消费

class AgentRequest(TypedDict):
    message: str
    session_id: str | None
    metadata: dict

class AgentResponse(TypedDict):
    answer: str
    state_id: str
    status: StateStatus

class AgentService(Protocol):
    """Application 层对外接口。"""

    def chat(self, request: AgentRequest) -> AgentResponse:
        ...
```

---

## Workflow（Phase11+）

```python
# workflow/node.py

class WorkflowNode(Protocol):
    id: str
    def execute(self, context: dict) -> dict: ...

class WorkflowEngine(Protocol):
    def run(self, graph: "WorkflowGraph", input: dict) -> dict: ...
    def interrupt(self, run_id: str) -> None: ...
    def resume(self, run_id: str, input: dict | None) -> dict: ...
```

---

## MCP（Phase14）

```python
# integrations/mcp/client.py

class MCPClient(Protocol):
    def discover_tools(self) -> list[ToolDefinition]: ...
    def call_tool(self, name: str, arguments: dict) -> Observation: ...
    def list_resources(self) -> list[dict]: ...
    def read_resource(self, uri: str) -> str: ...
```

---

## 接口演进规则

- 新增方法：minor 版本，更新 Interface Spec
-  breaking 变更：必须 ADR + 版本 bump
- 每 Phase 实现前 Review 本 Spec
