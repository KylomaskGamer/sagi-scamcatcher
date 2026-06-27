import asyncio
import json
import os


DEFAULT_CONFIG = {
    # Back-compat: older configs used "enabled" for OCR. Keep it, but prefer "ocr_enabled".
    "enabled": True,
    "ocr_enabled": True,
    "log_channel_id": None,
    "softban": True,
    "mercy": 12,
    "silly_mode": False,
    "honeypot_channel_ids": [],
    # How users get "staged" by automod.
    # - "ocr": run OCR on image attachments and match scam keywords.
    # - "threshold": match scam keywords in plain message text.
    "stage_types": ["ocr"],
    # Minimum matched scam keywords required to stage ("threshold" and "ocr" both use this).
    "spam_threshold": 4,
}


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


class ServerConfigStore:
    def __init__(self, path: str):
        self.path = path
        self.lock = asyncio.Lock()
        _ensure_parent_dir(self.path)

    def _load_all(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except FileNotFoundError:
            return {}
        except Exception:
            return {}
        return {}

    def _save_all(self, data: dict) -> None:
        _ensure_parent_dir(self.path)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    async def get(self, guild_id: int) -> dict:
        async with self.lock:
            all_data = self._load_all()
            raw = all_data.get(str(guild_id), {})
            cfg = dict(DEFAULT_CONFIG)
            if isinstance(raw, dict):
                cfg.update(raw)

            # normalize
            cfg["enabled"] = bool(cfg.get("enabled", True))
            cfg["ocr_enabled"] = bool(cfg.get("ocr_enabled", cfg["enabled"]))

            if cfg.get("log_channel_id") is not None:
                try:
                    cfg["log_channel_id"] = int(cfg["log_channel_id"])
                except Exception:
                    cfg["log_channel_id"] = None

            cfg["softban"] = bool(cfg.get("softban", True))
            cfg["silly_mode"] = bool(cfg.get("silly_mode", False))

            honeypot_ids_raw = cfg.get("honeypot_channel_ids", [])
            honeypot_ids: list[int] = []
            if isinstance(honeypot_ids_raw, (list, tuple, set)):
                for value in honeypot_ids_raw:
                    try:
                        honeypot_ids.append(int(value))
                    except Exception:
                        continue
            cfg["honeypot_channel_ids"] = sorted(set(honeypot_ids))

            stage_types_raw = cfg.get("stage_types", DEFAULT_CONFIG["stage_types"])
            stage_types: list[str] = []
            if isinstance(stage_types_raw, str):
                stage_types_raw = [stage_types_raw]
            if isinstance(stage_types_raw, (list, tuple, set)):
                for value in stage_types_raw:
                    if not isinstance(value, str):
                        continue
                    value = value.strip().lower()
                    if value in {"ocr", "threshold"}:
                        stage_types.append(value)
            if not stage_types:
                stage_types = list(DEFAULT_CONFIG["stage_types"])
            cfg["stage_types"] = sorted(set(stage_types))

            try:
                spam_threshold = int(cfg.get("spam_threshold", DEFAULT_CONFIG["spam_threshold"]))
            except Exception:
                spam_threshold = DEFAULT_CONFIG["spam_threshold"]
            if spam_threshold < 1:
                spam_threshold = 1
            if spam_threshold > 50:
                spam_threshold = 50
            cfg["spam_threshold"] = spam_threshold

            try:
                mercy = int(cfg.get("mercy", DEFAULT_CONFIG["mercy"]))
            except Exception:
                mercy = DEFAULT_CONFIG["mercy"]
            if mercy < 0:
                mercy = 0
            if mercy > 24:
                mercy = 24
            cfg["mercy"] = mercy

            return cfg

    async def set(self, guild_id: int, key: str, value):
        async with self.lock:
            all_data = self._load_all()
            guild_key = str(guild_id)
            if guild_key not in all_data or not isinstance(all_data.get(guild_key), dict):
                all_data[guild_key] = {}

            all_data[guild_key][key] = value
            self._save_all(all_data)

    async def reset(self, guild_id: int) -> None:
        async with self.lock:
            all_data = self._load_all()
            all_data.pop(str(guild_id), None)
            self._save_all(all_data)


_STORE = ServerConfigStore("data/server_config.json")


def get_store() -> ServerConfigStore:
    return _STORE
