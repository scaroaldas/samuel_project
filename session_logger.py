# session_logger.py
import json
import os
import datetime


class SessionLogger:
    def __init__(self, folder="sessions"):
        base = os.path.dirname(os.path.abspath(__file__))
        self.folder = os.path.join(base, folder)
        os.makedirs(self.folder, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.file_path = os.path.join(self.folder, f"session_{ts}.json")
        self.entries = []
        self._flush()

    def log(self, entry_type, content, extra=None):
        entry = {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "type": entry_type,
            "content": content,
        }
        if extra:
            entry.update(extra)
        self.entries.append(entry)
        self._flush()

    def _flush(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(
                {"session": os.path.basename(self.file_path), "entries": self.entries},
                f, ensure_ascii=False, indent=2
            )