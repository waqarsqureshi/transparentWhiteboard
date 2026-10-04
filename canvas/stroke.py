import time
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

@dataclass
class Point:
    x: float
    y: float
    pressure: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "pressure": round(self.pressure, 3),
            "timestamp": round(self.timestamp, 3),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Point":
        return cls(
            x=float(data["x"]),
            y=float(data["y"]),
            pressure=float(data.get("pressure", 1.0)),
            timestamp=float(data.get("timestamp", 0.0)),
        )

@dataclass
class Stroke:
    id: str
    tool: str = "pen"
    colour: str = "#FF3B30"
    width: float = 4.0
    opacity: float = 1.0
    points: List[Point] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float = field(default_factory=time.time)

    def add_point(self, x: float, y: float, pressure: float = 1.0) -> Point:
        p = max(0.05, min(1.0, pressure))
        pt = Point(x=x, y=y, pressure=p, timestamp=time.time())
        self.points.append(pt)
        self.end_time = pt.timestamp
        return pt

    def bounding_box(self) -> Tuple[float, float, float, float]:
        if not self.points:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        margin = self.width * 2.0
        return (min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin)

    def intersects_point(self, x: float, y: float, tolerance: float = 10.0) -> bool:
        if not self.points:
            return False
        min_x, min_y, max_x, max_y = self.bounding_box()
        if not (min_x - tolerance <= x <= max_x + tolerance and min_y - tolerance <= y <= max_y + tolerance):
            return False

        t2 = (tolerance + self.width / 2.0) ** 2
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            seg_len_sq = dx * dx + dy * dy
            if seg_len_sq == 0:
                dist_sq = (x - p1.x) ** 2 + (y - p1.y) ** 2
            else:
                t = max(0.0, min(1.0, ((x - p1.x) * dx + (y - p1.y) * dy) / seg_len_sq))
                proj_x = p1.x + t * dx
                proj_y = p1.y + t * dy
                dist_sq = (x - proj_x) ** 2 + (y - proj_y) ** 2
            if dist_sq <= t2:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool": self.tool,
            "colour": self.colour,
            "width": self.width,
            "opacity": self.opacity,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "points": [p.to_dict() for p in self.points],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stroke":
        pts = [Point.from_dict(p) for p in data.get("points", [])]
        return cls(
            id=data["id"],
            tool=data.get("tool", "pen"),
            colour=data.get("colour", "#FF3B30"),
            width=float(data.get("width", 4.0)),
            opacity=float(data.get("opacity", 1.0)),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            points=pts,
        )
