import subprocess
import threading
import time
import unittest

import frida

from frida_tools.reactor import Reactor
from frida_tools.tracer import MemoryRepository, TraceTarget, Tracer, TracerProfileBuilder, UI

from .data import target_program


class TestTracer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.target = subprocess.Popen([target_program], stdin=subprocess.PIPE)
        # TODO: improve injectors to handle injection into a process that hasn't yet finished initializing
        time.sleep(0.05)
        cls.session = frida.attach(cls.target.pid)

    @classmethod
    def tearDownClass(cls):
        cls.session.detach()
        cls.target.terminate()
        cls.target.stdin.close()
        cls.target.wait()

    def test_basics(self):
        done = threading.Event()
        reactor = Reactor(lambda reactor: done.wait())

        def start():
            tp = TracerProfileBuilder().include("open*")
            t = Tracer(reactor, MemoryRepository(), tp.build())
            t.start_trace(self.session, "late", {}, "qjs", UI())
            t.stop()
            reactor.stop()
            done.set()

        reactor.schedule(start)
        reactor.run()


class TestMemoryRepository(unittest.TestCase):
    def test_reuses_handlers_by_target_identifier(self):
        repo = MemoryRepository()
        events = []

        repo.on_create(lambda target, handler, source: events.append(("create", target.identifier, source, handler)))
        repo.on_load(lambda target, handler, source: events.append(("load", target.identifier, source, handler)))

        original = TraceTarget(7, "native", "libc.so", "open", "open", None)
        duplicate = TraceTarget(7, "native", "libc.so", "open", "open", None)

        first_handler = repo.ensure_handler(original)
        second_handler = repo.ensure_handler(duplicate)

        self.assertEqual(first_handler, second_handler)
        self.assertEqual(
            events,
            [
                ("create", 7, "memory", first_handler),
                ("load", 7, "memory", first_handler),
            ],
        )

    def test_tracer_ignores_messages_after_stop(self):
        reactor = Reactor(lambda reactor: None)
        tracer = Tracer(reactor, MemoryRepository(), TracerProfileBuilder().build())

        stale_script = object()
        tracer._script = None
        tracer._on_message(
            stale_script,
            {
                "type": "send",
                "payload": {
                    "type": "handlers:get",
                    "flavor": "native",
                    "baseId": 1,
                    "scopes": [{"name": "libc.so", "members": ["open"]}],
                },
            },
            None,
            UI(),
        )

    def test_tracer_ignores_stale_script_callbacks(self):
        scheduled = []

        class DummyReactor:
            def schedule(self, work):
                scheduled.append(work)

        class DummyUI(UI):
            def __init__(self):
                self.bridge_calls = []

            def try_handle_bridge_request(self, message, script):
                self.bridge_calls.append((message, script))
                return False

        tracer = Tracer(DummyReactor(), MemoryRepository(), TracerProfileBuilder().build())
        active_script = object()
        stale_script = object()
        ui = DummyUI()

        tracer._script = active_script
        tracer._on_script_message(stale_script, {"type": "send"}, None, ui)

        self.assertEqual(ui.bridge_calls, [])
        self.assertEqual(scheduled, [])


if __name__ == "__main__":
    unittest.main()
