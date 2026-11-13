import asyncio

import pytest

from srv1_core.events import EventBus


async def test_pattern_matching() -> None:
    bus = EventBus()
    system = bus.subscribe("system.*")
    everything = bus.subscribe()
    exact = bus.subscribe("audit", "plugin.demo.*")

    bus.publish("system.stats", {"cpu": 1})
    bus.publish("audit", {"id": 1})
    bus.publish("plugin.demo.tick")
    bus.close()

    assert [e.topic for e in [e async for e in system]] == ["system.stats"]
    assert [e.topic for e in [e async for e in exact]] == ["audit", "plugin.demo.tick"]
    received = [e async for e in everything]
    assert [e.seq for e in received] == [1, 2, 3]
    assert received[0].as_dict()["data"] == {"cpu": 1}


async def test_slow_subscriber_drops_oldest_and_never_blocks() -> None:
    bus = EventBus(queue_size=3)
    slow = bus.subscribe("t")
    for index in range(10):
        bus.publish("t", {"i": index})

    assert slow.dropped == 7
    assert slow.take_dropped() == 7
    assert slow.take_dropped() == 0
    bus.close()  # sentinel yana bitta eski hodisani siqib chiqaradi
    assert [e.data["i"] async for e in slow] == [8, 9]


async def test_unsubscribe_ends_iteration_and_stops_delivery() -> None:
    bus = EventBus()
    subscription = bus.subscribe("t")
    waiter = asyncio.create_task(anext(subscription))
    await asyncio.sleep(0)

    bus.unsubscribe(subscription)
    with pytest.raises(StopAsyncIteration):
        await waiter
    bus.publish("t")
    assert bus.subscriber_count == 0
    assert not bus.has_subscribers("t")


async def test_has_subscribers() -> None:
    bus = EventBus()
    bus.subscribe("system.*")
    assert bus.has_subscribers("system.stats")
    assert not bus.has_subscribers("audit")


async def test_subscribe_after_close_fails() -> None:
    bus = EventBus()
    bus.close()
    with pytest.raises(RuntimeError):
        bus.subscribe("t")
