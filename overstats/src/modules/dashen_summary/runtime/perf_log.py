import datetime
import os
import threading


_LOG_LOCK = threading.Lock()
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(_MODULE_DIR, "log.txt")


def append_perf_log(command, trace_id, stage, delta_ms=None, total_ms=None, extra=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    parts = [
        timestamp,
        f"command={command}",
        f"trace={trace_id}",
        f"stage={stage}",
    ]
    if delta_ms is not None:
        parts.append(f"delta_ms={int(delta_ms)}")
    if total_ms is not None:
        parts.append(f"total_ms={int(total_ms)}")
    if extra is not None:
        safe_extra = str(extra).replace("\r", " ").replace("\n", " | ")
        parts.append(f"extra={safe_extra}")

    try:
        with _LOG_LOCK:
            with open(LOG_PATH, "a", encoding="utf-8") as log_file:
                log_file.write(" | ".join(parts) + "\n")
    except Exception:
        # Logging must never block or break a user command.
        pass
