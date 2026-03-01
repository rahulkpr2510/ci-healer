# backend/app/services/sse_service.py

import asyncio
import json
import logging
from collections import defaultdict
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# run_id → list of subscribers (asyncio.Queue per connected client)
_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


async def subscribe(run_id: str) -> AsyncGenerator[str, None]:
    """
    SSE generator. Frontend connects here and receives live events.
    Usage in router:  return EventSourceResponse(subscribe(run_id))
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers[run_id].append(queue)

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                if event is None:   # None = stream closed signal
                    break
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive ping so connection stays open
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    finally:
        _subscribers[run_id].remove(queue)
        if not _subscribers[run_id]:
            del _subscribers[run_id]


async def broadcast(run_id: str, event: dict) -> None:
    """Push an event to all subscribers of a run."""
    queues = _subscribers.get(run_id, [])
    for queue in queues:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("SSE queue full for run %s — dropping event", run_id)


async def close_stream(run_id: str) -> None:
    """Signal all subscribers that the run is complete."""
    queues = _subscribers.get(run_id, [])
    for queue in queues:
        await queue.put(None)
