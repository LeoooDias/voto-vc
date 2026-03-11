import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """Base client with retry, rate limiting, and pagination helpers."""

    def __init__(self, base_url: str, delay_between_requests: float = 0.5):
        self.base_url = base_url.rstrip("/")
        self.delay = delay_between_requests

    async def close(self):
        pass  # no persistent client to close

    async def get(self, path: str, params: dict | None = None, retries: int = 5) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        for attempt in range(retries):
            try:
                await asyncio.sleep(self.delay)
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                wait = min(2 ** (attempt + 1), 60)
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}), retry in {wait}s: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(wait)
        return {}  # unreachable but satisfies type checker

    async def get_paginated(
        self,
        path: str,
        params: dict | None = None,
        page_key: str = "pagina",
        items_key: str = "itens",
        items_per_page: int = 100,
        data_path: str = "dados",
        max_pages: int | None = None,
    ) -> list[dict]:
        """Fetch all pages from a paginated endpoint."""
        params = params or {}
        params[items_key] = items_per_page
        all_items = []
        page = 1

        while True:
            params[page_key] = page
            data = await self.get(path, params=params)

            items = data.get(data_path, [])
            if not items:
                break

            all_items.extend(items)
            logger.info(f"Fetched page {page}: {len(items)} items (total: {len(all_items)})")

            if len(items) < items_per_page:
                break
            if max_pages and page >= max_pages:
                break
            page += 1

        return all_items
