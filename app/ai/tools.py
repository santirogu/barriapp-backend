"""Assistant tools: functions the LLM can call, bound to the current user.

Each tool has a JSON-schema input (for Claude tool-use) and an async executor that
hits the real backend (ownership-safe). ``select_tool`` is a pure, offline planner
used by the fallback agent when no LLM is configured.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from beanie import PydanticObjectId
from bson.errors import InvalidId

from app.orders import repository as orders_repo
from app.stores import repository as stores_repo
from app.users.models import User


@dataclass
class ToolContext:
    user: User
    order_id_hint: str | None = None


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    run: Callable[["ToolContext", dict[str, Any]], Awaitable[str]]


async def _get_order_status(ctx: ToolContext, args: dict[str, Any]) -> str:
    order_id = args.get("order_id") or ctx.order_id_hint
    order = None
    if order_id:
        try:
            order = await orders_repo.get_by_id(PydanticObjectId(order_id))
        except (InvalidId, ValueError):
            order = None
        if order is not None and order.client_id != ctx.user.id:
            order = None  # not the caller's order
    if order is None:
        assert ctx.user.id is not None
        recent = await orders_repo.list_by_client(ctx.user.id, skip=0, limit=1)
        order = recent[0] if recent else None
    if order is None:
        return "No encontré pedidos recientes tuyos."
    return f"El pedido {order.code} está en estado {order.status.value}."


async def _search_stores(ctx: ToolContext, args: dict[str, Any]) -> str:
    query = args.get("query")
    stores = await stores_repo.search(
        near=None, radius_meters=5000, category_id=None, query=query, skip=0, limit=5
    )
    if not stores:
        return "No encontré tiendas que coincidan."
    return "Tiendas disponibles: " + ", ".join(s.name for s in stores) + "."


def build_tools() -> list[Tool]:
    return [
        Tool(
            name="get_order_status",
            description=(
                "Consulta el estado de un pedido del usuario. Usa order_id si se "
                "provee; si no, toma el pedido más reciente del usuario."
            ),
            input_schema={
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
            },
            run=_get_order_status,
        ),
        Tool(
            name="search_stores",
            description="Busca tiendas de barrio por nombre.",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
            run=_search_stores,
        ),
    ]


_ORDER_TRIGGERS = ("donde", "dónde", "estado", "seguimiento", "rastre", "llega")


def select_tool(message: str, tool_names: list[str]) -> str | None:
    """Pure intent planner for the offline fallback agent (at most one tool)."""
    m = message.lower()
    if (
        "get_order_status" in tool_names
        and ("pedido" in m or "orden" in m)
        and any(t in m for t in _ORDER_TRIGGERS)
    ):
        return "get_order_status"
    if "search_stores" in tool_names and ("tienda" in m or "tiendas" in m):
        return "search_stores"
    return None
