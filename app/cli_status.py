"""Terminal-native status presentation for interactive STS CLI requests."""

import sys
import threading
from time import perf_counter
from typing import TextIO

from app.runtime_status import RuntimeStatusEvent


_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
_STAGE_LABELS = {
    "loading_agent": "Loading agent",
    "reading_memory": "Reading memory",
    "searching_knowledge": "Searching knowledge",
    "building_prompt": "Building prompt",
    "waiting_for_model": "Waiting for local model",
    "processing_response": "Processing response",
    "saving_memory": "Saving memory",
    "complete": "Complete",
    "timeout": "Local model timed out",
    "failure": "Request failed",
}


class CLIStatusRenderer:
    """Render the latest runtime stage in one terminal line."""

    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        refresh_interval: float = 0.1,
    ) -> None:
        self._stream = stream or sys.stdout
        self._refresh_interval = refresh_interval
        self._interactive = bool(getattr(self._stream, "isatty", lambda: False)())
        self._started_at = 0.0
        self._event: RuntimeStatusEvent | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_width = 0

    def __enter__(self) -> "CLIStatusRenderer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()

    def start(self) -> None:
        if not self._interactive or self._thread is not None:
            return
        self._started_at = perf_counter()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._render_loop,
            name="sts-cli-status",
            daemon=True,
        )
        self._thread.start()

    def update(self, event: RuntimeStatusEvent) -> None:
        if not self._interactive:
            return
        with self._lock:
            self._event = event

    def stop(self) -> None:
        thread = self._thread
        if thread is None:
            return
        self._stop_event.set()
        thread.join()
        self._thread = None
        self._clear_line()

    def _render_loop(self) -> None:
        frame_index = 0
        while not self._stop_event.wait(self._refresh_interval):
            with self._lock:
                event = self._event
            if event is None:
                continue
            elapsed = max(0.0, perf_counter() - self._started_at)
            label = _STAGE_LABELS[event.stage]
            context = event.agent_name
            if event.model:
                context = f"{context} · {event.model}"
            line = (
                f"{_SPINNER_FRAMES[frame_index % len(_SPINNER_FRAMES)]} "
                f"{label}… {elapsed:.1f}s  [{context}]"
            )
            self._write_line(line)
            frame_index += 1

    def _write_line(self, line: str) -> None:
        padding = " " * max(0, self._last_width - len(line))
        self._stream.write(f"\r{line}{padding}")
        self._stream.flush()
        self._last_width = len(line)

    def _clear_line(self) -> None:
        if self._last_width:
            self._stream.write(f"\r{' ' * self._last_width}\r")
            self._stream.flush()
            self._last_width = 0
