import abc
from typing import List
from canvas.stroke import Stroke

class Command(abc.ABC):
    @abc.abstractmethod
    def execute(self): pass
    @abc.abstractmethod
    def undo(self): pass
    @abc.abstractmethod
    def redo(self): pass

class AddStrokeCommand(Command):
    def __init__(self, strokes_list: List[Stroke], stroke: Stroke):
        self.strokes_list = strokes_list
        self.stroke = stroke
    def execute(self):
        self.strokes_list.append(self.stroke)
    def undo(self):
        if self.strokes_list and self.strokes_list[-1] == self.stroke:
            self.strokes_list.pop()
        elif self.stroke in self.strokes_list:
            self.strokes_list.remove(self.stroke)
    def redo(self):
        self.strokes_list.append(self.stroke)

class EraseStrokesCommand(Command):
    def __init__(self, strokes_list: List[Stroke], removed_strokes_with_indices):
        self.strokes_list = strokes_list
        self.removed_strokes_with_indices = removed_strokes_with_indices
    def execute(self):
        for _, stroke in reversed(self.removed_strokes_with_indices):
            if stroke in self.strokes_list:
                self.strokes_list.remove(stroke)
    def undo(self):
        for index, stroke in self.removed_strokes_with_indices:
            if index <= len(self.strokes_list):
                self.strokes_list.insert(index, stroke)
            else:
                self.strokes_list.append(stroke)
    def redo(self):
        self.execute()

class ClearCanvasCommand(Command):
    def __init__(self, strokes_list: List[Stroke]):
        self.strokes_list = strokes_list
        self.cleared_strokes = list(strokes_list)
    def execute(self):
        self.strokes_list.clear()
    def undo(self):
        self.strokes_list.extend(self.cleared_strokes)
    def redo(self):
        self.strokes_list.clear()

class UndoRedoManager:
    def __init__(self, max_history: int = 100):
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_history = max_history

    def execute_command(self, command: Command):
        command.execute()
        self.undo_stack.append(command)
        self.redo_stack.clear()
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        cmd = self.undo_stack.pop()
        cmd.undo()
        self.redo_stack.append(cmd)
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        cmd = self.redo_stack.pop()
        cmd.redo()
        self.undo_stack.append(cmd)
        return True

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
