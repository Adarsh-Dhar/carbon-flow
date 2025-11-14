---
inclusion: fileMatch
fileMatchPattern: '**/agents.py'
---

# CrewAI Implementation Patterns

This steering file is automatically included when working with agent files.

## Agent Architecture Patterns

### Tool Result Caching

Always implement a global cache for tool results to enable fallback execution when LLM rate limits are hit:

```python
TOOL_RESULT_CACHE: dict[str, Any] = {}

def _with_debug_logs(tool_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        TOOL_RESULT_CACHE[tool_name] = result  # Cache for fallback
        return result
    return wrapper
```

### Fallback Execution Pattern

When Gemini returns RESOURCE_EXHAUSTED, execute tools deterministically using cached results:

```python
try:
    result = crew.kickoff()
except Exception as exc:
    message = str(exc)
    if "RESOURCE_EXHAUSTED" not in message:
        raise
    
    # Fallback to deterministic execution
    print("\nGemini rate limit encountered. Falling back to deterministic tool execution.")
    result = execute_tools_from_cache()
```

### Tool Argument Schema

Always define a base schema that accepts CrewAI's security_context:

```python
class _EmptyToolArgs(BaseModel):
    security_context: dict | None = None
    
    if ConfigDict:
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - pydantic < 2.x
        class Config:
            extra = "forbid"
```

For tools with parameters:

```python
class S3ReaderArgs(BaseModel):
    bucket_name: str
    object_key: str | None = None
    security_context: dict | None = None
    
    if ConfigDict:
        model_config = ConfigDict(extra="forbid")
```

### Tool Wrapper Pattern

Wrap all tool functions with debug logging:

```python
from datetime import datetime

def _with_debug_logs(tool_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        timestamp = datetime.utcnow().isoformat()
        debug_kwargs = dict(kwargs)
        security_context = debug_kwargs.pop("security_context", None)
        
        print(
            f"[DEBUG {timestamp}] Tool `{tool_name}` invoked "
            f"with args={args} kwargs={debug_kwargs} security_context={security_context}"
        )
        
        result = func(*args, **debug_kwargs)
        TOOL_RESULT_CACHE[tool_name] = result
        
        print(
            f"[DEBUG {timestamp}] Tool `{tool_name}` completed "
            f"with result_type={type(result).__name__}"
        )
        
        return result
    return wrapper
```

### Agent Definition Pattern

Define agents with clear roles and comprehensive backstories:

```python
agent_name = Agent(
    role="Descriptive Role Name",
    goal="Clear, measurable goal statement",
    backstory=(
        "Detailed backstory explaining the agent's purpose, "
        "responsibilities, and reliability requirements. "
        "Should be 2-3 sentences that give the agent context."
    ),
    tools=[tool1, tool2, tool3],
    verbose=True,
)
```

### Tool Registration Pattern

Register tools with CrewAI using the Tool class:

```python
from crewai.tools.base_tool import Tool

tool_name = Tool(
    name="Action-oriented tool name",
    description="Clear description of what the tool does and what it returns.",
    func=_with_debug_logs("Tool name", actual_function),
    args_schema=ToolArgsSchema
)
```

## Task Patterns

### Task Definition

```python
from crewai import Task

task_name = Task(
    description="Clear description of what needs to be done.",
    expected_output="Specific format and content of the expected output.",
    agent=assigned_agent,
    context=[previous_task1, previous_task2],  # Optional: pass outputs from previous tasks
)
```

### Task Context Passing

Use the `context` parameter to make previous task outputs available:

```python
task_final = Task(
    description="Consolidate all data sources.",
    expected_output="A success message with file path.",
    agent=consolidation_agent,
    context=[task_fetch_1, task_fetch_2, task_fetch_3],
)
```

## Crew Orchestration

### Sequential Process Pattern

Use sequential processing for reliability:

```python
from crewai import Crew, Process

crew = Crew(
    agents=[agent1, agent2],
    tasks=[task1, task2, task3, task4],
    process=Process.sequential,
    verbose=True,
)
```

### Crew Execution Pattern

```python
def run_cycle() -> dict:
    """Execute a single crew cycle."""
    print("Kicking off the Crew...")
    
    try:
        result = crew.kickoff()
    except Exception as exc:
        message = str(exc)
        if "RESOURCE_EXHAUSTED" not in message:
            raise
        
        print("\nGemini rate limit encountered. Falling back to deterministic execution.")
        result = fallback_execution()
    
    print("\nCrew run completed. Final result:")
    print(result)
    return result
```

## Common Patterns for This Project

### Cache-Based Fallback Functions

Create fallback functions that use cached tool results:

```python
def normalize_and_merge_from_cache() -> Any:
    """Normalize and merge using cached DataFrames from previous tools."""
    df1 = TOOL_RESULT_CACHE.get("Fetch data source 1")
    df2 = TOOL_RESULT_CACHE.get("Fetch data source 2")
    
    if df1 is None or df2 is None:
        missing = [name for name, df in [("Source 1", df1), ("Source 2", df2)] if df is None]
        raise ValueError(f"Missing results from: {', '.join(missing)}")
    
    result = merge_function(df1, df2)
    TOOL_RESULT_CACHE["Merge result"] = result
    return result
```

### Environment Configuration

Configure LLM from environment at module level:

```python
from src.utils.env_config import configure_llm_from_env

configure_llm_from_env()  # Call at module level before defining agents
```

### Error Handling in Tools

Return error dicts instead of raising exceptions:

```python
def fetch_data_tool() -> dict:
    try:
        # Fetch data logic
        return {"data": result}
    except Exception as e:
        return {
            "error": "Failed to fetch data",
            "details": str(e)
        }
```

## Anti-Patterns to Avoid

### Don't Use Bare Exceptions

```python
# BAD
try:
    result = risky_operation()
except:
    pass

# GOOD
try:
    result = risky_operation()
except SpecificException as exc:  # noqa: BLE001 if broad exception is intentional
    print(f"ERROR: Operation failed - {exc}")
    raise
```

### Don't Hardcode Credentials

```python
# BAD
api_key = "abc123xyz"

# GOOD
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable not set")
```

### Don't Skip Tool Caching

```python
# BAD
def tool_wrapper(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)  # No caching!
    return wrapper

# GOOD
def tool_wrapper(tool_name, func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        TOOL_RESULT_CACHE[tool_name] = result  # Cache for fallback
        return result
    return wrapper
```

### Don't Ignore security_context

```python
# BAD
class ToolArgs(BaseModel):
    param1: str
    # Missing security_context!

# GOOD
class ToolArgs(BaseModel):
    param1: str
    security_context: dict | None = None
```
