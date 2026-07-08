from collections import defaultdict
from typing import Any
import asyncio

_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

async def subscribe(channel: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers[channel].append(q)
    return q

def unsubscribe(channel: str, q: asyncio.Queue):
    if q in _subscribers[channel]:
        _subscribers[channel].remove(q)

async def publish(channel: str, event: dict[str, Any]):
    for q in list(_subscribers[channel]):
        await q.put(event)
