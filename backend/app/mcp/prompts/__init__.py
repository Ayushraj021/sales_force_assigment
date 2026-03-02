"""
MCP Prompts Module.

Provides workflow prompt templates for common analytics scenarios.
"""

from app.mcp.prompts.workflow_prompts import (
    WorkflowPrompt,
    get_available_prompts,
    get_prompt_by_name,
)

__all__ = [
    "WorkflowPrompt",
    "get_available_prompts",
    "get_prompt_by_name",
]
