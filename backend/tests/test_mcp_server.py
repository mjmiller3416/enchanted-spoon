"""The MCP server's tools: one for everything a person can do, behaving like the app.

Every route must have a tool or a reason in ``EXCLUDED``; every tool must
name a real route and carry proper hints. Representative calls go through
the real routes as the token's user (read, write, delete, an app refusal,
another account's data), and ``generate_recipe_photo`` chains its routes.
"""

import json
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.mcp import dispatch, server
from app.api.mcp.tools import EXCLUDED, EXCLUDED_PREFIXES, TOOLS, ToolContext, build
from app.services.oauth_service import AuthorizeRequest, OAuthService, pkce_s256
from tests.test_mcp_oauth import MCP_HEADERS, REDIRECT, factory  # noqa: F401  (fixture)
from app.main import app

VERIFIER = "v" * 50


def token_for(session_factory, user_id: int) -> str:
    """An access token for ``user_id``, minted through the OAuth service."""
    with session_factory() as session:
        service = OAuthService(session)
        client = service.register_client([REDIRECT], "ChatGPT", "none", None).client
        code = service.issue_code(
            AuthorizeRequest(
                client_id=client.client_id,
                client_name="ChatGPT",
                redirect_uri=REDIRECT,
                code_challenge=pkce_s256(VERIFIER),
                state=None,
                scope="mcp",
                resource=None,
            ),
            user_id,
        )
        return service.exchange_code(client, code=code, redirect_uri=REDIRECT, code_verifier=VERIFIER, resource=None).access_token


@pytest.fixture()
def mcp(factory):  # noqa: F811
    client = TestClient(app)
    tokens = {1: token_for(factory, 1), 2: token_for(factory, 2)}

    def call_raw(name: str, user: int = 1, **arguments: Any) -> dict:
        r = client.post(
            "/api/mcp",
            json={"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
            headers={**MCP_HEADERS, "Authorization": f"Bearer {tokens[user]}"},
        )
        assert r.status_code == 200, r.text
        return r.json()["result"]

    return call_raw


def ok(result: dict) -> Any:
    assert result["isError"] is False, result["content"][0]["text"]
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
    return result["structuredContent"]


# ── Coverage ────────────────────────────────────────────────────────────────
def test_every_user_route_has_a_tool():
    internal = dispatch.internal_app()
    covered = {endpoint for spec in TOOLS for endpoint in spec.endpoints}
    missing = []
    for path, operations in internal.openapi()["paths"].items():
        if any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        for method in operations:
            key = (method.upper(), path)
            if key not in covered and key not in EXCLUDED:
                missing.append(key)
    assert not missing, f"Routes with no MCP tool (add one, or a reason in EXCLUDED): {missing}"


def test_tools_name_real_routes_and_carry_hints():
    built = build(dispatch.internal_app())  # raises if a tool names a missing route
    routes = {(m.upper(), p) for p, ops in dispatch.internal_app().openapi()["paths"].items() for m in ops}
    for spec in TOOLS:
        assert re.fullmatch(r"[a-z][a-z0-9_]{2,63}", spec.name), spec.name
        assert 15 <= len(spec.description) <= 400, spec.name
        for endpoint in spec.endpoints:
            assert endpoint in routes, (spec.name, endpoint)
        hints = spec.annotations()
        assert set(hints) == {"readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"}
        assert not (hints["readOnlyHint"] and hints["destructiveHint"]), spec.name
        if spec.method == "GET" and spec.kind == "read":
            assert hints["readOnlyHint"]
        if spec.method == "DELETE" and spec.path and spec.path.count("{") <= 1 and spec.kind == "read":
            pytest.fail(f"{spec.name} deletes but is marked read-only")
        assert built[spec.name].schema["type"] == "object"
        if "AI generation" in spec.description:
            assert not hints["readOnlyHint"], f"{spec.name} spends AI allowance; mark it a write"
    assert sum(1 for s in TOOLS if s.open_world) == 1  # only send_feedback leaves the app


def test_tools_list_payload_is_valid():
    tools = server.list_tools_payload()["tools"]
    assert len(tools) == len(TOOLS)
    for tool in tools:
        assert set(tool) == {"name", "title", "description", "inputSchema", "annotations"}
        assert "$ref" not in json.dumps(tool["inputSchema"])


# ── Calls ───────────────────────────────────────────────────────────────────
def test_create_read_update_delete_a_recipe(mcp):
    created = ok(
        mcp(
            "create_recipe",
            recipe_name="Weeknight Chili",
            recipe_category="Mexican",
            meal_type="Dinner",
            servings=4,
            prep_time=10,
            cook_time=30,
            directions="Brown the beef.\nAdd beans and simmer.",
            ingredients=[{"ingredient_name": "Ground beef", "ingredient_category": "Meat", "quantity": 1, "unit": "lb"}],
        )
    )
    recipe_id = created["id"]

    cards = ok(mcp("list_recipes", search_term="Chili"))
    assert [c["id"] for c in cards["items"]] == [recipe_id]

    full = ok(mcp("get_recipe", recipe_id=recipe_id))
    assert full["ingredients"][0]["ingredient_name"] == "Ground beef"

    updated = ok(mcp("update_recipe", recipe_id=recipe_id, notes="Better the next day."))
    assert updated["notes"] == "Better the next day."

    ok(mcp("delete_recipe", recipe_id=recipe_id))
    gone = mcp("get_recipe", recipe_id=recipe_id)
    assert gone["isError"] is True
    assert "404" in gone["content"][0]["text"]


def test_meal_planner_and_shopping_list(mcp):
    recipe = ok(
        mcp(
            "create_recipe",
            recipe_name="Pancakes",
            recipe_category="Breakfast",
            ingredients=[{"ingredient_name": "Flour", "ingredient_category": "Baking", "quantity": 2, "unit": "cup"}],
        )
    )
    meal = ok(mcp("create_meal", meal_name="Sunday breakfast", main_recipe_id=recipe["id"]))
    entry = ok(mcp("add_meal_to_planner", meal_id=meal["id"]))
    planned = ok(mcp("list_planner_entries"))
    assert [e["id"] for e in planned["items"]] == [entry["id"]]

    ok(mcp("add_shopping_item", ingredient_name="Maple syrup", quantity=1))
    shopping = json.dumps(ok(mcp("get_shopping_list")))
    assert "Maple syrup" in shopping and "Flour" in shopping

    done = ok(mcp("mark_planner_entry_cooked", entry_id=entry["id"]))
    assert done["is_completed"] is True


def test_settings_patch_keeps_other_sections(mcp):
    ok(mcp("update_settings", appearance={"theme": "dark"}))
    settings = ok(mcp("get_settings"))
    assert settings["appearance"]["theme"] == "dark"
    assert settings["shoppingList"]["categorySortOrder"] == "alphabetical"


def test_another_accounts_recipe_is_out_of_reach(mcp):
    recipe = ok(mcp("create_recipe", recipe_name="Private Stew", recipe_category="Soup"))
    other = mcp("get_recipe", user=2, recipe_id=recipe["id"])
    assert other["isError"] is True
    assert ok(mcp("list_recipes", user=2))["items"] == []


def test_bad_arguments_are_explained(mcp):
    unknown = mcp("list_recipes", colour="red")
    assert unknown["isError"] and "colour" in unknown["content"][0]["text"]
    missing = mcp("get_recipe")
    assert missing["isError"] and "recipe_id" in missing["content"][0]["text"]
    invalid = mcp("create_recipe", recipe_name="", recipe_category="Soup")
    assert invalid["isError"] and "recipe_name" in invalid["content"][0]["text"]


def test_unknown_tool_is_a_jsonrpc_error(factory):  # noqa: F811
    client = TestClient(app)
    token = token_for(factory, 1)
    r = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "nope", "arguments": {}}},
        headers={**MCP_HEADERS, "Authorization": f"Bearer {token}"},
    )
    assert r.json()["error"]["code"] == -32602


class FakeContext(ToolContext):
    """Records calls and answers the photo routes without Gemini or Cloudinary."""

    def __init__(self) -> None:
        super().__init__(user_id=1)
        object.__setattr__(self, "calls", [])

    async def call(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((method, path, kwargs))
        if path == "/api/recipes/5" and method == "GET":
            return {"id": 5, "recipe_name": "Tomato Soup"}
        if path == "/api/ai/image-generation":
            return {"success": True, "reference_image_data": "aGVsbG8="}
        if path == "/api/upload/base64":
            return {"success": True, "path": "https://img.example/5.png"}
        if path == "/api/recipes/5" and method == "PUT":
            return {"id": 5, "recipe_name": "Tomato Soup", **kwargs["json_body"]}
        raise AssertionError(path)


@pytest.mark.anyio
async def test_generate_recipe_photo_generates_uploads_and_attaches():
    spec = next(s for s in TOOLS if s.name == "generate_recipe_photo")
    ctx = FakeContext()
    result = await spec.handler(ctx, {"recipe_id": 5})
    assert result == {"recipe_id": 5, "recipe_name": "Tomato Soup", "image_url": "https://img.example/5.png"}
    assert [(m, p) for m, p, _ in ctx.calls] == [
        ("GET", "/api/recipes/5"),
        ("POST", "/api/ai/image-generation"),
        ("POST", "/api/upload/base64"),
        ("PUT", "/api/recipes/5"),
    ]
    assert ctx.calls[1][2]["json_body"] == {"recipe_name": "Tomato Soup"}
    assert ctx.calls[3][2]["json_body"] == {"reference_image_path": "https://img.example/5.png", "banner_image_path": "https://img.example/5.png"}


def test_image_payloads_are_left_out_of_results():
    result = server.tool_result({"success": True, "recipe": {"recipe_name": "X"}, "reference_image_data": "A" * 5000, "banner_image_data": None})
    assert result["structuredContent"] == {"success": True, "recipe": {"recipe_name": "X"}, "photo_omitted": True}
