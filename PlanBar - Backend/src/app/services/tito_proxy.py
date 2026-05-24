from typing import Any

import httpx

from app.config import settings


class TiTOProxy:
    def __init__(self) -> None:
        self.api_url = settings.tito_api_url
        headers = {}
        if settings.tito_api_key:
            headers["Authorization"] = f"Bearer {settings.tito_api_key}"
        self.client = httpx.AsyncClient(headers=headers, timeout=30.0)

    async def submit_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self.client.post(f"{self.api_url}/jobs", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_job_status(self, job_id: int) -> dict[str, Any]:
        response = await self.client.get(f"{self.api_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    async def retry_job(self, job_id: int) -> dict[str, Any]:
        response = await self.client.post(f"{self.api_url}/jobs/{job_id}/retry")
        response.raise_for_status()
        return response.json()

    async def check_health(self) -> bool:
        try:
            response = await self.client.get(f"{self.api_url}/health", timeout=5.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self.client.aclose()


tito_proxy = TiTOProxy()
