from __future__ import annotations

from typing import TypedDict


class SpaceRoute(TypedDict):
    space_id: str
    endpoint: str


# Maps each supported action to the Space that can perform it.
SPACE_REGISTRY: dict[str, SpaceRoute] = {
    "check_order_status": {
        "space_id": "space://store-support",
        "endpoint": "http://127.0.0.1:8101/tasks",
    },
    "cancel_order": {
        "space_id": "space://store-orders",
        "endpoint": "http://127.0.0.1:8102/tasks",
    },
}


def resolve_route(action: str) -> SpaceRoute:
    """
    Find the Space that supports the requested action.
    """

    route = SPACE_REGISTRY.get(action)

    if route is None:
        raise LookupError(
            f"No Space is registered for action '{action}'."
        )

    # Return a copy so callers cannot modify the registry itself.
    return route.copy()