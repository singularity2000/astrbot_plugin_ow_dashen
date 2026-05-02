from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from overstats.src.client.apiclient import DashenAPIClient
except ModuleNotFoundError:
    from src.client.apiclient import DashenAPIClient

from .render import RenderedImage, render_bnet_search_result
from .requests import BnetSearchRequests, BnetSearchResult


@dataclass(frozen=True)
class BnetSearchOutput:
    result: BnetSearchResult
    image: Optional[RenderedImage] = None


class BnetSearchModule:
    def __init__(self, api_client: Optional[DashenAPIClient] = None) -> None:
        self.requests = BnetSearchRequests(api_client)

    async def search(self, bnet_id: str, *, render: bool = False) -> BnetSearchOutput:
        result = await self.requests.search(bnet_id)
        image = render_bnet_search_result(result) if render else None
        return BnetSearchOutput(result=result, image=image)

    async def resolve_customer_token(self, bnet_id: str) -> str:
        output = await self.search(bnet_id, render=False)
        return output.result.customer_token


bnet_search_module = BnetSearchModule()
