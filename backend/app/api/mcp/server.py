"""app/api/mcp/server.py

The MCP protocol itself: JSON-RPC 2.0 over Streamable HTTP, stateless, JSON
responses only (no SSE, no sessions, no server-initiated messages).

Hand-rolled rather than the ``mcp`` SDK: the server needs four methods
(initialize, ping, tools/list, tools/call) and the SDK would add a session
manager with its own lifespan and a large dependency tree for nothing this
server uses.

``handle_message`` answers one JSON-RPC message for a given user; the HTTP
route (app/api/mcp/__init__.py) checks the access token first.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.api.mcp import dispatch
from app.api.mcp.tools import BuiltTool, ToolContext, build

logger = logging.getLogger(__name__)

SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
LATEST_VERSION = SUPPORTED_VERSIONS[0]
SERVER_INFO = {"name": "enchanted-spoon", "title": "Enchanted Spoon", "version": "1.0.0"}

INSTRUCTIONS = """\
Enchanted Spoon is the person's recipe box, meal planner and shopping list.
Everything here acts as them and is exactly what they'd see in the app.

How it fits together:
- Recipes have ingredients (name, aisle category, quantity, unit) and directions.
- A meal is a main recipe plus up to 3 side recipes. The planner (called the
  Menu in the app) is an ordered list of meals to cook (20 uncooked at most);
  marking one cooked builds the cooking streak and history.
- The shopping list fills itself from the planner's meals (each entry's
  shopping mode: all, produce_only or none) plus items added by hand.

Look ids up before using them: list_recipes, list_meals, list_planner_entries,
get_shopping_list. get_overview is a good first call. To save a recipe from a
link or an idea, use import_recipe_from_url or generate_recipe, then
create_recipe. Tools marked as calling AI generation spend the account's AI
allowance; use them when asked.
"""

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602

_tools: Optional[Dict[str, BuiltTool]] = None


def tools() -> Dict[str, BuiltTool]:
    """Every tool, built once from the internal app's routes."""
    global _tools
    if _tools is None:
        _tools = build(dispatch.internal_app())
    return _tools


def _error(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _result(msg_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def list_tools_payload() -> Dict[str, Any]:
    """The tools/list result."""
    return {
        "tools": [
            {
                "name": name,
                "title": tool.spec.display_title,
                "description": tool.spec.description,
                "inputSchema": tool.schema,
                "annotations": tool.spec.annotations(),
            }
            for name, tool in tools().items()
        ]
    }


def _strip_images(value: Any) -> Any:
    """Drop base64 image payloads (megabytes ChatGPT can't use); say a photo was left out."""
    if isinstance(value, list):
        return [_strip_images(v) for v in value]
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            if key.endswith("_image_data"):
                if item:
                    out["photo_omitted"] = True
                continue
            out[key] = _strip_images(item)
        return out
    return value


def tool_result(data: Any) -> Dict[str, Any]:
    """A successful tools/call result: structuredContent plus the same JSON as text."""
    data = _strip_images(data)
    if data is None or data == {}:
        structured: Dict[str, Any] = {"ok": True}
    elif isinstance(data, dict):
        structured = data
    elif isinstance(data, list):
        structured = {"items": data, "count": len(data)}
    else:
        structured = {"result": data}
    text = json.dumps(structured, separators=(",", ":"), default=str)
    return {"content": [{"type": "text", "text": text}], "structuredContent": structured, "isError": False}


def tool_error(message: str) -> Dict[str, Any]:
    """A failed tools/call result the model can read and act on."""
    return {"content": [{"type": "text", "text": message}], "isError": True}


async def call_tool(name: str, arguments: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Run one tool as ``ctx.user_id``; app refusals come back as isError results."""
    tool = tools()[name]
    spec = tool.spec
    allowed = set(tool.schema.get("properties", {}))
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        return tool_error(
            f"Unknown argument(s) for {name}: {', '.join(unknown)}. Allowed: {', '.join(sorted(allowed)) or 'none'}."
        )
    missing = [n for n in tool.schema.get("required", []) if arguments.get(n) is None]
    if missing:
        return tool_error(f"Missing required argument(s) for {name}: {', '.join(missing)}.")
    try:
        if spec.handler is not None:
            data = await spec.handler(ctx, arguments)
        else:
            merged = {**spec.fixed, **arguments}
            path = spec.path or ""
            for arg in tool.path_args:
                path = path.replace("{" + arg + "}", str(merged[arg]))
            params = {k: merged[k] for k in tool.query_args if k in merged}
            body: Any = None
            if spec.body_arg:
                body = merged.get(spec.body_arg)
            elif tool.body_args or any(k in spec.fixed for k in spec.hidden):
                body = {k: merged[k] for k in [*tool.body_args, *spec.hidden] if k in merged}
            data = await ctx.call(spec.method or "GET", path, params=params, json_body=body)
    except dispatch.ToolCallError as exc:
        return tool_error(str(exc))
    except Exception:
        logger.exception("MCP tool %s failed", name)
        return tool_error(f"{name} failed with an unexpected error. Try again, or do it in the app.")
    return tool_result(data)


async def handle_message(message: Any, ctx: ToolContext) -> Optional[Dict[str, Any]]:
    """Answer one JSON-RPC message; None for notifications (and responses) that need no reply."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, INVALID_REQUEST, "Expected a JSON-RPC 2.0 message.")
    method = message.get("method")
    msg_id = message.get("id")
    if method is None:
        return None  # a response from the client; nothing to do
    if "id" not in message:
        return None  # notification (notifications/initialized, cancelled...)
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _error(msg_id, INVALID_PARAMS, "params must be an object.")

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_VERSIONS else LATEST_VERSION
        return _result(
            msg_id,
            {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            },
        )
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, list_tools_payload())
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or name not in tools():
            return _error(msg_id, INVALID_PARAMS, f"Unknown tool: {name}")
        if not isinstance(arguments, dict):
            return _error(msg_id, INVALID_PARAMS, "arguments must be an object.")
        return _result(msg_id, await call_tool(name, arguments, ctx))
    if method in ("resources/list", "prompts/list"):
        key = method.split("/")[0]
        return _result(msg_id, {key: []})
    return _error(msg_id, METHOD_NOT_FOUND, f"Method not found: {method}")
