## What changed

Describe the change and its user-visible effect.

## Safety

Explain how overwrite prevention, rollback, Undo, and sidecar defaults are
preserved. Include sanitized before/after filename examples when relevant.

## Verification

- [ ] `ruff check src tests scripts packaging/entrypoint.py`
- [ ] `QT_QPA_PLATFORM=offscreen pytest`
- [ ] I tested only on copied or disposable media files.
- [ ] I updated public documentation for user-visible behavior.
