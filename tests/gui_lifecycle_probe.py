"""Exercise UI shutdown with simulated calls, never rename files."""

import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

from reelabel import api, core, updates
from reelabel.gui.history import HistoryDialog
from reelabel.gui.main_window import MainWindow

mode = sys.argv[1]
app = QApplication([])
with tempfile.TemporaryDirectory(
    prefix="reelabel-lifecycle-",
) as temporary:
    path = Path(temporary)

    def checker():
        time.sleep(0.35 if mode == "scan_update" else 0.2)
        return updates.UpdateCheckResult(
            "0.2.0",
            "0.2.0",
            False,
            "https://github.com/ares-projects-H/reelabel/releases/tag/v0.2.0",
        )

    window = MainWindow(
        settings_store=QSettings(str(path / "settings.ini"), QSettings.IniFormat),
        update_checker=checker,
    )
    window.show()
    if mode in ("scan", "scan_update"):

        def simulated_scan(options, cancelled):
            time.sleep(0.2)
            if cancelled():
                raise core.ScanCancelled()
            return api.ScanReport(options, core.Report())

        api.scan = simulated_scan
        window.path_edit.setText(str(path))
        window._start_scan()
    if mode in ("update", "scan_update"):
        window._start_update_check()
    if mode in ("apply", "undo"):
        window._operation_kind = mode
        window._operation_context = None
        if mode == "undo":
            dialog = HistoryDialog(path, window)
            window._history_dialog = dialog
            dialog.open()
            dialog.set_busy(True)
        window._begin_file_operation("Probe", "Simulated operation")

        def simulated_operation():
            time.sleep(0.2)
            return SimpleNamespace(renamed=0, restored=0, deleted_sidecars=0, errors=[])

        window.operations.start(simulated_operation)
    close_returns = []
    QTimer.singleShot(20, lambda: close_returns.append(window.close()))
    QTimer.singleShot(5000, app.quit)
    start = time.monotonic()
    result = app.exec()
    elapsed = time.monotonic() - start
    print(
        mode,
        "elapsed",
        round(elapsed, 3),
        "close_returns",
        close_returns,
        "scan",
        window._scan_thread,
        "update",
        window.update_controller.thread,
        "operation",
        window.operations.thread,
        "visible",
        window.isVisible(),
        "exec",
        result,
    )
    assert 0.15 < elapsed < 4, (mode, elapsed)
    assert (
        window._scan_thread is None
        and window.update_controller.thread is None
        and window.operations.thread is None
    )
    assert not window.isVisible()
