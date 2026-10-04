import os
import json
from dataclasses import dataclass, field, asdict
from typing import List

@dataclass
class WhiteboardConfig:
    default_color: str = "#FF3B30"
    default_width: int = 4
    default_opacity: float = 1.0
    highlighter_opacity: float = 0.4
    selected_display: int = 0
    autosave_interval_minutes: int = 5
    enable_autosave: bool = True
    start_in_fullscreen: bool = True
    smoothing_factor: float = 0.5
    toolbar_position: List[int] = field(default_factory=lambda: [100, 40])
    toolbar_collapsed: bool = False
    favorite_colors: List[str] = field(default_factory=lambda: [
        "#FF3B30", "#34C759", "#007AFF", "#FFCC00", "#000000", "#FFFFFF"
    ])

class ConfigManager:
    @staticmethod
    def get_config_dir() -> str:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = os.path.expanduser("~")
        config_dir = os.path.join(appdata, "TransparentWhiteboard")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    @staticmethod
    def get_config_path() -> str:
        return os.path.join(ConfigManager.get_config_dir(), "settings.json")

    @classmethod
    def load(cls) -> WhiteboardConfig:
        path = cls.get_config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return WhiteboardConfig(**{k: v for k, v in data.items() if k in WhiteboardConfig.__dataclass_fields__})
            except Exception as e:
                print(f"Warning: Failed to load config ({e}), using defaults.")
        return WhiteboardConfig()

    @classmethod
    def save(cls, config: WhiteboardConfig):
        path = cls.get_config_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(config), f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
