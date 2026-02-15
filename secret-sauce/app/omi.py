"""Omi API client — store memories back to Omi."""

import os

import httpx

OMI_BASE = "https://api.omi.me"


async def store_memory(
    app_id: str,
    uid: str,
    api_key: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    """Store a memory to Omi via the integrations API.

    POST /v2/integrations/{app_id}/memories?uid={uid}
    """
    url = f"{OMI_BASE}/v2/integrations/{app_id}/memories"
    payload = {
        "memories": [
            {
                "content": content,
                "tags": tags or ["secret-sauce"],
            }
        ],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            params={"uid": uid},
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


def get_vault_config() -> tuple[str, str]:
    """Return (VAULT_APP_ID, VAULT_API_KEY) from env."""
    return (
        os.environ.get("VAULT_APP_ID", ""),
        os.environ.get("VAULT_API_KEY", ""),
    )


def get_oracle_config() -> tuple[str, str]:
    """Return (ORACLE_APP_ID, ORACLE_API_KEY) from env."""
    return (
        os.environ.get("ORACLE_APP_ID", ""),
        os.environ.get("ORACLE_API_KEY", ""),
    )


def get_dev_keys() -> tuple[str, str]:
    """Return (DEVICE_A_DEV_KEY, DEVICE_B_DEV_KEY) from env."""
    return (
        os.environ.get("DEVICE_A_DEV_KEY", ""),
        os.environ.get("DEVICE_B_DEV_KEY", ""),
    )


async def create_action_item(
    dev_api_key: str,
    description: str,
    completed: bool = False,
    due_at: str | None = None,
) -> dict:
    """Create an action item via the Developer API.

    POST /v1/dev/user/action-items
    Auth: Bearer omi_dev_...
    """
    url = f"{OMI_BASE}/v1/dev/user/action-items"
    payload: dict = {"description": description, "completed": completed}
    if due_at:
        payload["due_at"] = due_at

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {dev_api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


async def get_action_items(
    dev_api_key: str,
    completed: bool | None = None,
    limit: int = 50,
) -> list:
    """Retrieve action items via the Developer API.

    GET /v1/dev/user/action-items
    """
    url = f"{OMI_BASE}/v1/dev/user/action-items"
    params: dict = {"limit": limit}
    if completed is not None:
        params["completed"] = str(completed).lower()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {dev_api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

