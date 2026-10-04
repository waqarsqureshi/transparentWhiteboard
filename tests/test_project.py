import os
import tempfile
from canvas.stroke import Stroke
from persistence.project import ProjectPersistence

def test_save_and_load_project():
    stroke = Stroke(id="s1", tool="pen", colour="#FF3B30", width=4.0)
    stroke.add_point(10, 10, 0.5)
    with tempfile.NamedTemporaryFile(suffix=".whiteboard", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        success = ProjectPersistence.save_project(tmp_path, [stroke], 1920, 1080)
        assert success is True
        loaded = ProjectPersistence.load_project(tmp_path)
        assert loaded is not None
        assert len(loaded["strokes"]) == 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
