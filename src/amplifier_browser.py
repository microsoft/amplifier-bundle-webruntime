"""
Amplifier Browser - Full Amplifier running in Pyodide with WebGPU.

This module provides browser-compatible implementations that enable
the REAL amplifier-core to run in Pyodide, including:
- WebGPU Provider with manual tool calling support
- Browser-native tools (todo, web)
- Full AmplifierSession with real orchestrator
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Callable, AsyncIterator, TYPE_CHECKING

# amplifier-core imports
# pyright: reportMissingImports=false
from amplifier_core.interfaces import Provider, ContextManager, Tool, Orchestrator
from amplifier_core.message_models import (
    ChatRequest,
    ChatResponse,
    Message,
    Usage,
    TextBlock,
    ToolSpec,
)
from amplifier_core.models import ProviderInfo, ModelInfo, ToolResult
from amplifier_core.hooks import HookRegistry
from amplifier_core import events

logger = logging.getLogger(__name__)

# JS bridge functions injected by main.js
if TYPE_CHECKING:

    async def js_llm_complete(messages_json: str, tools_json: str | None) -> str: ...
    async def js_llm_stream(
        messages_json: str, on_chunk: Callable[[str], None]
    ) -> str: ...
    async def js_web_fetch(url: str) -> str: ...


# =============================================================================
# WebGPU Provider - Full Provider with Tool Calling
# =============================================================================


class WebGPUProvider(Provider):
    """
    Provider that uses WebGPU via JavaScript bridge.

    Implements the full amplifier-core Provider protocol.
    Note: WebLLM's native function calling is WIP, so we use manual tool calling.
    """

    def __init__(self, model_id: str = "Hermes-3-Llama-3.1-8B-q4f16_1-MLC"):
        self.model_id = model_id
        self._name = "webgpu"

    @property
    def name(self) -> str:
        return self._name

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            id="webgpu",
            display_name="WebGPU Local LLM",
            description="Local LLM inference via WebGPU - runs entirely in browser",
            supports_streaming=True,
            supports_tools=True,  # We support manual tool calling
            supports_vision=False,
        )

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id=self.model_id,
                display_name=self.model_id,
                context_window=4096,  # WebLLM default
                supports_tools=True,
                supports_vision=False,
            )
        ]

    async def complete(
        self,
        request: ChatRequest,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate a completion using WebGPU."""
        # Convert messages to format expected by JS bridge
        messages_data = []
        for msg in request.messages:
            if isinstance(msg.content, str):
                msg_dict = {"role": msg.role, "content": msg.content}
            else:
                # Handle content blocks
                text_parts = []
                for block in msg.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
                    elif hasattr(block, "output"):
                        # Tool result
                        text_parts.append(str(block.output))
                msg_dict = {"role": msg.role, "content": "\n".join(text_parts)}

            if msg.name:
                msg_dict["name"] = msg.name
            messages_data.append(msg_dict)

        messages_json = json.dumps(messages_data)

        # Call JavaScript LLM function (no tools param - we use manual calling)
        result_json = await js_llm_complete(messages_json, None)
        result = json.loads(result_json)

        content_text = result.get("content", "")

        return ChatResponse(
            content=[TextBlock(text=content_text)],
            tool_calls=None,  # We handle tool calls manually in orchestrator
            usage=Usage(
                input_tokens=result.get("usage", {}).get("prompt_tokens", 0),
                output_tokens=result.get("usage", {}).get("completion_tokens", 0),
                total_tokens=result.get("usage", {}).get("total_tokens", 0),
            ),
            finish_reason=result.get("finish_reason", "stop"),
        )

    async def stream(
        self,
        request: ChatRequest,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResponse]:
        """Generate a streaming completion using WebGPU."""
        # For now, fall back to non-streaming
        response = await self.complete(request, **kwargs)
        yield response


# =============================================================================
# Browser-Native Tools
# =============================================================================


class BrowserTodoTool(Tool):
    """
    Todo list management tool - pure in-memory state.
    Works entirely in browser with no external dependencies.
    """

    def __init__(self):
        self._todos: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "todo"

    def get_spec(self) -> ToolSpec:
        return ToolSpec(
            name="todo",
            description="Manage a task list. Actions: 'create' to replace all items, 'update' to modify, 'list' to show current items.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "list"],
                        "description": "Action to perform",
                    },
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "Task description",
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                },
                            },
                        },
                        "description": "List of tasks (for create/update)",
                    },
                },
                "required": ["action"],
            },
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "list")

        if action == "list":
            return ToolResult(
                success=True,
                output=json.dumps(
                    {
                        "status": "listed",
                        "count": len(self._todos),
                        "todos": self._todos,
                    }
                ),
            )

        if action in ("create", "update"):
            todos = kwargs.get("todos", [])
            self._todos = todos

            pending = sum(1 for t in todos if t.get("status") == "pending")
            in_progress = sum(1 for t in todos if t.get("status") == "in_progress")
            completed = sum(1 for t in todos if t.get("status") == "completed")

            return ToolResult(
                success=True,
                output=json.dumps(
                    {
                        "status": "created" if action == "create" else "updated",
                        "count": len(todos),
                        "pending": pending,
                        "in_progress": in_progress,
                        "completed": completed,
                    }
                ),
            )

        return ToolResult(
            success=False,
            output=f"Unknown action: {action}",
        )


class BrowserWebTool(Tool):
    """
    Web fetch tool using browser's fetch API.
    Limited to CORS-allowed URLs.
    """

    @property
    def name(self) -> str:
        return "web_fetch"

    def get_spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_fetch",
            description="Fetch content from a URL. Note: Limited to CORS-allowed URLs due to browser security.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                },
                "required": ["url"],
            },
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        url = kwargs.get("url", "")
        if not url:
            return ToolResult(success=False, output="URL is required")

        try:
            # Call JS fetch function
            result = await js_web_fetch(url)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=f"Fetch failed: {str(e)}")


# =============================================================================
# Browser Orchestrator - Manual Tool Calling
# =============================================================================


class BrowserOrchestrator(Orchestrator):
    """
    Orchestrator with MANUAL tool calling for WebLLM.

    Since WebLLM's native function calling is WIP, we:
    1. Include tool descriptions in the system prompt
    2. Instruct the model to output <tool_call> JSON when it wants to use tools
    3. Parse the output for tool calls
    4. Execute tools and add results to context
    5. Loop until model gives final response without tool calls
    """

    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations

    def _build_tool_instructions(self, tools: dict[str, Tool]) -> str:
        """Build tool usage instructions for the system prompt."""
        if not tools:
            return ""

        tool_descriptions = []
        for name, tool in tools.items():
            spec = tool.get_spec()
            params = spec.parameters.get("properties", {})
            param_list = []
            for k, v in params.items():
                param_list.append(
                    f"  - {k} ({v.get('type', 'any')}): {v.get('description', '')}"
                )
            param_str = "\n".join(param_list) if param_list else "  (no parameters)"
            tool_descriptions.append(
                f"### {name}\n{spec.description}\nParameters:\n{param_str}"
            )

        return f"""

## TOOLS

You have access to these tools:

{chr(10).join(tool_descriptions)}

## HOW TO USE TOOLS

When you need to use a tool, output EXACTLY this format:
<tool_call>
{{"name": "TOOL_NAME", "arguments": {{"param": "value"}}}}
</tool_call>

IMPORTANT:
- Use ONLY the exact tool names shown above
- Output the <tool_call> tag on its own line
- Wait for the tool result before continuing
- If you don't need tools, just respond normally without any <tool_call> tags
"""

    def _parse_tool_call(self, text: str) -> tuple[dict | None, str]:
        """
        Parse a tool call from text.
        Returns (tool_call_dict, text_before_call) or (None, original_text).
        """
        # Look for <tool_call>...</tool_call>
        match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL)
        if match:
            try:
                tool_call = json.loads(match.group(1))
                before_text = text[: match.start()].strip()
                return tool_call, before_text
            except json.JSONDecodeError as e:
                print(f"[DEBUG] Failed to parse tool call JSON: {e}")
                pass

        return None, text

    async def execute(
        self,
        prompt: str,
        context: ContextManager,
        providers: dict[str, Provider],
        tools: dict[str, Tool],
        hooks: HookRegistry,
    ) -> str:
        """Execute the agentic loop with manual tool calling."""
        provider = next(iter(providers.values()))

        # Add user message
        await context.add_message({"role": "user", "content": prompt})
        await hooks.emit(events.PROMPT_SUBMIT, {"prompt": prompt})

        iterations = 0
        while iterations < self.max_iterations:
            iterations += 1
            print(f"[ORCHESTRATOR] Iteration {iterations}")

            # Get messages
            messages = await context.get_messages_for_request()

            # Convert to Message objects
            msg_objects = [
                Message(
                    role=m["role"], content=m.get("content", ""), name=m.get("name")
                )
                for m in messages
            ]

            # Create request
            request = ChatRequest(messages=msg_objects)

            # Get completion
            await hooks.emit(events.PROVIDER_REQUEST, {"model": provider.model_id})
            response = await provider.complete(request)
            await hooks.emit(events.PROVIDER_RESPONSE, {"response": response})

            # Extract text
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            print(f"[ORCHESTRATOR] Response: {response_text[:200]}...")

            # Check for tool call
            tool_call, before_text = self._parse_tool_call(response_text)

            if tool_call:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("arguments", {})

                print(f"[TOOL_CALL] {tool_name}({tool_args})")

                await hooks.emit(
                    events.TOOL_PRE, {"tool": tool_name, "arguments": tool_args}
                )

                # Add any text before the tool call
                if before_text:
                    await context.add_message(
                        {"role": "assistant", "content": before_text}
                    )

                # Execute tool
                if tool_name in tools:
                    tool = tools[tool_name]
                    try:
                        result = await tool.execute(**tool_args)
                        output = (
                            result.output
                            if result.success
                            else f"Error: {result.output}"
                        )
                    except Exception as e:
                        output = f"Tool error: {str(e)}"
                else:
                    output = (
                        f"Unknown tool: {tool_name}. Available: {list(tools.keys())}"
                    )

                print(f"[TOOL_RESULT] {output[:200]}...")

                await hooks.emit(
                    events.TOOL_POST, {"tool": tool_name, "result": output}
                )

                # Add tool result as user message (for manual calling pattern)
                await context.add_message(
                    {
                        "role": "user",
                        "content": f"[Tool Result for {tool_name}]\n{output}\n\nPlease continue with your response based on this result.",
                    }
                )

                continue

            # No tool call - final response
            await context.add_message({"role": "assistant", "content": response_text})
            return response_text

        return "Max iterations reached."


# =============================================================================
# Browser Context Manager
# =============================================================================


class BrowserContextManager(ContextManager):
    """Simple in-memory context manager for browser use."""

    def __init__(self, max_messages: int = 100):
        self._messages: list[dict[str, Any]] = []
        self._max_messages = max_messages
        self._system_prompt: str | None = None
        self._tool_instructions: str = ""

    async def add_message(self, message: dict[str, Any]) -> None:
        self._messages.append(message)
        if len(self._messages) > self._max_messages:
            system_msgs = [m for m in self._messages if m.get("role") == "system"]
            other_msgs = [m for m in self._messages if m.get("role") != "system"]
            keep_count = self._max_messages - len(system_msgs)
            self._messages = system_msgs + other_msgs[-keep_count:]

    async def get_messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    async def get_messages_for_request(
        self,
        token_budget: int | None = None,
        provider: Any | None = None,
    ) -> list[dict[str, Any]]:
        messages = []

        # Combine system prompt with tool instructions
        full_system = (self._system_prompt or "") + self._tool_instructions
        if full_system:
            messages.append({"role": "system", "content": full_system})

        for msg in self._messages:
            if msg.get("role") != "system":
                messages.append(msg)

        return messages

    async def set_messages(self, messages: list[dict[str, Any]]) -> None:
        self._messages = list(messages)

    async def clear(self) -> None:
        self._messages = []

    def set_system_prompt(self, prompt: str) -> None:
        self._system_prompt = prompt

    def set_tool_instructions(self, instructions: str) -> None:
        self._tool_instructions = instructions


# =============================================================================
# Browser Amplifier Session
# =============================================================================


class BrowserAmplifierSession:
    """
    Browser-compatible Amplifier session using real amplifier-core components.
    """

    DEFAULT_SYSTEM_PROMPT = """You are Amplifier, an AI assistant running entirely in the user's browser via WebGPU.

You are helpful, concise, and honest. If you don't know something, say so."""

    def __init__(
        self,
        model_id: str = "Hermes-3-Llama-3.1-8B-q4f16_1-MLC",
        system_prompt: str | None = None,
    ):
        self.model_id = model_id
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.session_id = str(uuid.uuid4())

        self.provider = WebGPUProvider(model_id=model_id)
        self.context = BrowserContextManager()
        self.orchestrator = BrowserOrchestrator()
        self.hooks = HookRegistry()

        # Register browser-native tools
        self.tools: dict[str, Tool] = {
            "todo": BrowserTodoTool(),
            "web_fetch": BrowserWebTool(),
        }

        self._initialized = False
        print(f"BrowserAmplifierSession created with model: {model_id}")

    async def initialize(self) -> None:
        if self._initialized:
            return

        # Set system prompt
        self.context.set_system_prompt(self.system_prompt)

        # Build and set tool instructions
        tool_instructions = self.orchestrator._build_tool_instructions(self.tools)
        self.context.set_tool_instructions(tool_instructions)

        self._initialized = True
        print(
            f"BrowserAmplifierSession initialized with tools: {list(self.tools.keys())}"
        )

    async def execute(self, prompt: str) -> str:
        if not self._initialized:
            await self.initialize()

        response = await self.orchestrator.execute(
            prompt=prompt,
            context=self.context,
            providers={"webgpu": self.provider},
            tools=self.tools,
            hooks=self.hooks,
        )

        return response

    async def get_history(self) -> list[dict[str, Any]]:
        return await self.context.get_messages()

    async def clear_history(self) -> None:
        await self.context.clear()
        print("Conversation history cleared")

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt
        self.context.set_system_prompt(prompt)
        print(f"System prompt updated ({len(prompt)} chars)")

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool
        # Rebuild tool instructions
        tool_instructions = self.orchestrator._build_tool_instructions(self.tools)
        self.context.set_tool_instructions(tool_instructions)
        print(f"Tool registered: {tool.name}")


# =============================================================================
# Factory function for JavaScript
# =============================================================================


def create_session(
    model_id: str = "Hermes-3-Llama-3.1-8B-q4f16_1-MLC",
    system_prompt: str | None = None,
) -> BrowserAmplifierSession:
    """Create a new browser Amplifier session."""
    return BrowserAmplifierSession(
        model_id=model_id,
        system_prompt=system_prompt,
    )


__all__ = [
    "BrowserAmplifierSession",
    "WebGPUProvider",
    "BrowserContextManager",
    "BrowserOrchestrator",
    "BrowserTodoTool",
    "BrowserWebTool",
    "create_session",
]

print("Amplifier Browser (with Manual Tool Calling) loaded!")
