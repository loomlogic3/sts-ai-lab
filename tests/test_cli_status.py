import io
import threading
import time

import pytest

from app.cli_status import CLIStatusRenderer
from app.runtime_status import RuntimeStatusEvent


class InteractiveStream(io.StringIO):
    def isatty(self):
        return True


def active_status_threads():
    return [thread for thread in threading.enumerate() if thread.name == "sts-cli-status"]


def test_interactive_renderer_displays_stage_elapsed_time_and_cleans_up():
    stream = InteractiveStream()

    with CLIStatusRenderer(stream=stream, refresh_interval=0.001) as renderer:
        renderer.update(
            RuntimeStatusEvent("waiting_for_model", "STS Mentor", "sts-fast")
        )
        time.sleep(0.01)
        assert active_status_threads()

    output = stream.getvalue()
    assert "Waiting for local model" in output
    assert "STS Mentor · sts-fast" in output
    assert "s  [" in output
    assert output.endswith("\r")
    assert active_status_threads() == []


@pytest.mark.parametrize(
    "raised",
    [None, TimeoutError("timeout"), RuntimeError("failure"), KeyboardInterrupt()],
)
def test_renderer_cleans_up_for_all_exit_paths(raised):
    stream = InteractiveStream()

    with pytest.raises(BaseException) if raised else _does_not_raise():
        with CLIStatusRenderer(stream=stream, refresh_interval=0.001) as renderer:
            renderer.update(RuntimeStatusEvent("waiting_for_model", "STS Mentor"))
            time.sleep(0.003)
            if raised:
                raise raised

    assert active_status_threads() == []


def test_repeated_requests_do_not_leak_threads():
    for _ in range(5):
        with CLIStatusRenderer(
            stream=InteractiveStream(),
            refresh_interval=0.001,
        ) as renderer:
            renderer.update(RuntimeStatusEvent("building_prompt", "code_agent"))
            time.sleep(0.002)

    assert active_status_threads() == []


def test_repeated_cancellation_does_not_leak_threads():
    for _ in range(5):
        with pytest.raises(KeyboardInterrupt):
            with CLIStatusRenderer(
                stream=InteractiveStream(),
                refresh_interval=0.001,
            ) as renderer:
                renderer.update(
                    RuntimeStatusEvent("waiting_for_model", "STS Mentor")
                )
                time.sleep(0.002)
                raise KeyboardInterrupt

        assert active_status_threads() == []


def test_non_tty_renderer_is_silent_and_does_not_start_thread():
    stream = io.StringIO()

    with CLIStatusRenderer(stream=stream) as renderer:
        renderer.update(RuntimeStatusEvent("waiting_for_model", "STS Mentor"))

    assert stream.getvalue() == ""
    assert "\r" not in stream.getvalue()
    assert active_status_threads() == []


class _does_not_raise:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc_value, traceback):
        return False
