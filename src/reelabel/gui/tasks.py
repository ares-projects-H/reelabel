"""Finite background calls whose results are consumed only after thread cleanup."""

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot


class TaskThread(QThread):
    """Run a callable without an event loop or any access to GUI widgets.

    Only run() writes result/error. The GUI reads them after finished and wait(),
    including thread-local teardown, before dropping the last Python reference.
    """

    def __init__(self, call: Callable, parent=None):
        super().__init__(parent)
        self.call = call
        self.result = None
        self.error: Exception | None = None

    def run(self) -> None:
        try:
            self.result = self.call()
        except Exception as exc:
            self.error = exc.with_traceback(None)


class OperationRunner(QObject):
    """Serialize file-changing operations; never interrupt a rename or undo."""

    completed = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread: TaskThread | None = None

    @property
    def busy(self) -> bool:
        return self.thread is not None

    def start(self, call: Callable) -> None:
        if self.busy:
            raise RuntimeError("An operation is already running")
        self.thread = TaskThread(call, self)
        self.thread.finished.connect(self._finished)
        self.thread.start()

    @Slot()
    def _finished(self) -> None:
        task = self.thread
        task.wait()
        self.thread = None
        result, error = task.result, task.error
        task.deleteLater()
        self.completed.emit(result, error)
