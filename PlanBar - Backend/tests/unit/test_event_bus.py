"""Unit tests for the EventBus singleton."""

from app.core.event_bus import EventBus, event_bus


class TestEventBus:
    def test_dispatch_calls_subscriber(self):
        bus = EventBus()
        events = []

        def callback(etype, data):
            events.append((etype, data))

        bus.subscribe("test.event", callback)
        bus.dispatch("test.event", {"key": "value"})

        assert len(events) == 1
        assert events[0] == ("test.event", {"key": "value"})

    def test_wildcard_subscriber(self):
        bus = EventBus()
        events = []

        def callback(etype, data):
            events.append(etype)

        bus.subscribe("*", callback)
        bus.dispatch("event.a", {})
        bus.dispatch("event.b", {})

        assert events == ["event.a", "event.b"]

    def test_no_subscriber_does_not_raise(self):
        bus = EventBus()
        bus.dispatch("nonexistent", {})

    def test_subscriber_error_does_not_affect_others(self):
        bus = EventBus()
        calls = []

        def failing(etype, data):
            raise ValueError("oops")

        def good(etype, data):
            calls.append("called")

        bus.subscribe("test.event", failing)
        bus.subscribe("test.event", good)
        bus.dispatch("test.event", {})

        assert calls == ["called"]

    def test_multiple_event_types(self):
        bus = EventBus()
        events = []

        def callback(etype, data):
            events.append(etype)

        bus.subscribe("event.one", callback)
        bus.subscribe("event.two", callback)
        bus.dispatch("event.one", {})
        bus.dispatch("event.two", {})

        assert events == ["event.one", "event.two"]

    def test_singleton_behavior(self):
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2

    def test_clear_state_between_tests(self):
        bus = EventBus()
        bus._subscribers.clear()
        assert bus._subscribers == {}

    def test_dispatch_with_wildcard_and_specific(self):
        bus = EventBus()
        wildcard_calls = []
        specific_calls = []

        def wildcard(etype, data):
            wildcard_calls.append(etype)

        def specific(etype, data):
            specific_calls.append(etype)

        bus.subscribe("*", wildcard)
        bus.subscribe("specific.event", specific)
        bus.dispatch("specific.event", {})

        assert wildcard_calls == ["specific.event"]
        assert specific_calls == ["specific.event"]

    def test_event_bus_module_instance(self):
        from app.core.event_bus import event_bus as module_bus
        assert isinstance(module_bus, EventBus)
        assert module_bus is EventBus()
