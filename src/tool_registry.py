from typing import Dict, Any, Callable
from src.tools import TOOL_REGISTRY

class ToolRegistryError(Exception):
    pass

def register_tools():
    # Registry already populated in tools module
    return TOOL_REGISTRY

def get_tool(name: str) -> Dict[str, Any]:
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        raise ToolRegistryError(f"Unknown tool: {name}")
    return tool

def list_tools() -> list[str]:
    return list(TOOL_REGISTRY.keys())

def validate_arguments(tool_name: str, args: dict):
    tool = get_tool(tool_name)
    input_model = tool["input_model"]
    return input_model(**args)

def execute_tool(tool_name: str, args: dict):
    tool = get_tool(tool_name)
    # Validate input first
    validated = tool["input_model"](**args)
    # Execute with validated data as dict
    result = tool["func"](validated.model_dump(mode='python'))
    # Validate output
    output_model = tool["output_model"]
    output_model(**result)
    return result
