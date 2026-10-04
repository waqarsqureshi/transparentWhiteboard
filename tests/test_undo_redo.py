from canvas.stroke import Stroke
from commands.undo_redo_manager import UndoRedoManager, AddStrokeCommand

def test_undo_redo_add_stroke():
    strokes = []
    manager = UndoRedoManager()
    s1 = Stroke(id="s1")
    cmd = AddStrokeCommand(strokes, s1)
    manager.execute_command(cmd)
    assert len(strokes) == 1
    manager.undo()
    assert len(strokes) == 0
    manager.redo()
    assert len(strokes) == 1
