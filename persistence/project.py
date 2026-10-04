import json
import time
from typing import List, Dict, Any, Optional
from canvas.stroke import Stroke
from app.constants import APP_VERSION

class ProjectPersistence:
    @staticmethod
    def save_project(file_path: str, strokes: List[Stroke], width: int, height: int, display_index: int = 0) -> bool:
        data = {
            "version": APP_VERSION,
            "created_at": time.time(),
            "display": display_index,
            "canvas": {"width": width, "height": height},
            "strokes": [s.to_dict() for s in strokes],
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    @staticmethod
    def load_project(file_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "strokes" not in data:
                return None
            return {
                "version": data.get("version", "1.0.0"),
                "display": data.get("display", 0),
                "canvas": data.get("canvas", {"width": 1920, "height": 1080}),
                "strokes": [Stroke.from_dict(s) for s in data.get("strokes", [])],
            }
        except Exception as e:
            print(f"Error loading project: {e}")
            return None
