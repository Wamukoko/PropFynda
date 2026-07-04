import json
from typing import Optional

from app.config import PLATFORMS_FILE
from app.scraper.base import BaseAdapter
from app.scraper.adapters.buyrentkenya import BuyRentKenyaAdapter
from app.scraper.adapters.generic import GenericAdapter
from app.scraper.adapters.jiji import JijiAdapter

ADAPTER_CLASSES: dict[str, type[BaseAdapter]] = {
    "buyrentkenya": BuyRentKenyaAdapter,
    "generic": GenericAdapter,
    "jiji": JijiAdapter,
}


def load_platforms() -> list[dict]:
    with open(PLATFORMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_platform(platform_id: str) -> Optional[dict]:
    for p in load_platforms():
        if p["id"] == platform_id:
            return p
    return None


def build_adapter(platform_config: dict) -> BaseAdapter:
    adapter_key = platform_config.get("adapter", "generic")
    adapter_cls = ADAPTER_CLASSES.get(adapter_key, GenericAdapter)
    return adapter_cls(platform_config)
