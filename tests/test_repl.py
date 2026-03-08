import unittest

from frida_tools.repl import REPLApplication


class TestREPLApplication(unittest.TestCase):
    def test_ignores_stale_script_callbacks(self):
        scheduled = []

        class DummyReactor:
            def schedule(self, work):
                scheduled.append(work)

        app = REPLApplication.__new__(REPLApplication)
        active_script = object()
        stale_script = object()
        bridge_calls = []

        app._script = active_script
        app._reactor = DummyReactor()
        app.try_handle_bridge_request = lambda message, script: bridge_calls.append((message, script)) or False
        app._process_message = lambda message, data: None

        app._on_script_message(stale_script, {"type": "send"}, None)

        self.assertEqual(bridge_calls, [])
        self.assertEqual(scheduled, [])

    def test_schedules_active_script_callbacks(self):
        scheduled = []
        processed = []

        class DummyReactor:
            def schedule(self, work):
                scheduled.append(work)

        app = REPLApplication.__new__(REPLApplication)
        active_script = object()
        bridge_calls = []
        message = {"type": "send"}

        app._script = active_script
        app._reactor = DummyReactor()
        app.try_handle_bridge_request = lambda incoming, script: bridge_calls.append((incoming, script)) or False
        app._process_message = lambda incoming, data: processed.append((incoming, data))

        app._on_script_message(active_script, message, b"data")

        self.assertEqual(bridge_calls, [(message, active_script)])
        self.assertEqual(len(scheduled), 1)

        scheduled[0]()

        self.assertEqual(processed, [(message, b"data")])


if __name__ == "__main__":
    unittest.main()
