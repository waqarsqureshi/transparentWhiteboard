import math
import time
import uuid
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


def _clip_segment_outside_circle(
    x1: float, y1: float, x2: float, y2: float, cx: float, cy: float, r: float
) -> Tuple[bool, List[Tuple[float, float, float, float, bool]]]:
    """
    Clips line segment (x1, y1)->(x2, y2) against circle (cx, cy, r).
    Returns (was_clipped, list_of_surviving_segments), where each segment is
    (sx1, sy1, sx2, sy2, includes_original_end).
    """
    dx = x2 - x1
    dy = y2 - y1
    a = dx * dx + dy * dy
    fx = x1 - cx
    fy = y1 - cy
    r2 = r * r

    if a < 1e-6:
        if fx * fx + fy * fy <= r2:
            return True, []
        return False, [(x1, y1, x2, y2, True)]

    b = fx * dx + fy * dy
    c = fx * fx + fy * fy - r2
    disc = b * b - a * c
    if disc <= 0.0:
        return False, [(x1, y1, x2, y2, True)]

    sqrt_disc = math.sqrt(disc)
    t_enter = (-b - sqrt_disc) / a
    t_exit = (-b + sqrt_disc) / a

    t1 = max(0.0, t_enter)
    t2 = min(1.0, t_exit)
    if t1 >= t2:
        return False, [(x1, y1, x2, y2, True)]

    seg_len = math.sqrt(a)
    pieces: List[Tuple[float, float, float, float, bool]] = []
    if t1 * seg_len >= 2.0:
        pieces.append((x1, y1, x1 + t1 * dx, y1 + t1 * dy, False))
    if (1.0 - t2) * seg_len >= 2.0:
        pieces.append((x1 + t2 * dx, y1 + t2 * dy, x2, y2, True))
    return True, pieces


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

        if len(self.points) == 1:
            p = self.points[0]
            return (x - p.x) ** 2 + (y - p.y) ** 2 <= t2

        if self.tool == "rectangle" and len(self.points) >= 2:
            p1 = self.points[0]
            p2 = self.points[-1]
            rx1, ry1 = min(p1.x, p2.x), min(p1.y, p2.y)
            rx2, ry2 = max(p1.x, p2.x), max(p1.y, p2.y)
            edges = [
                ((rx1, ry1), (rx2, ry1)),
                ((rx2, ry1), (rx2, ry2)),
                ((rx2, ry2), (rx1, ry2)),
                ((rx1, ry2), (rx1, ry1)),
            ]
            for (ea_x, ea_y), (eb_x, eb_y) in edges:
                dx = eb_x - ea_x
                dy = eb_y - ea_y
                seg_len_sq = dx * dx + dy * dy
                if seg_len_sq == 0:
                    dist_sq = (x - ea_x) ** 2 + (y - ea_y) ** 2
                else:
                    t = max(0.0, min(1.0, ((x - ea_x) * dx + (y - ea_y) * dy) / seg_len_sq))
                    proj_x = ea_x + t * dx
                    proj_y = ea_y + t * dy
                    dist_sq = (x - proj_x) ** 2 + (y - proj_y) ** 2
                if dist_sq <= t2:
                    return True
            return False

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

    def erase_circle(self, cx: float, cy: float, radius: float) -> Tuple[bool, List["Stroke"]]:
        """
        Physical rubber partial erasure: erases the portion of this stroke inside
        circle (cx, cy, radius), returning (was_modified, surviving_strokes).
        Works with pen, highlighter, line, arrow, and rectangle strokes.
        """
        if not self.points:
            return False, []
        if not self.intersects_point(cx, cy, tolerance=radius):
            return False, [self]

        eff_r = radius + self.width * 0.35

        # 1. Straight Line or Arrow: exact analytical segment-circle clipping
        if self.tool in ("line", "arrow") and len(self.points) >= 2:
            p0, p1 = self.points[0], self.points[-1]
            clipped, segs = _clip_segment_outside_circle(p0.x, p0.y, p1.x, p1.y, cx, cy, eff_r)
            if not clipped:
                return False, [self]
            result: List[Stroke] = []
            for sx1, sy1, sx2, sy2, has_end in segs:
                piece_tool = self.tool if (self.tool == "arrow" and has_end) else "line"
                s = Stroke(
                    id=str(uuid.uuid4()),
                    tool=piece_tool,
                    colour=self.colour,
                    width=self.width,
                    opacity=self.opacity,
                    start_time=self.start_time,
                    end_time=self.end_time,
                )
                s.add_point(sx1, sy1, p0.pressure)
                s.add_point(sx2, sy2, p1.pressure)
                result.append(s)
            return True, result

        # 2. Rectangle: decompose into 4 edge lines and clip each edge against the eraser circle
        if self.tool == "rectangle" and len(self.points) >= 2:
            p0, p1 = self.points[0], self.points[-1]
            rx1, ry1 = min(p0.x, p1.x), min(p0.y, p1.y)
            rx2, ry2 = max(p0.x, p1.x), max(p0.y, p1.y)
            edges = [
                (rx1, ry1, rx2, ry1),
                (rx2, ry1, rx2, ry2),
                (rx2, ry2, rx1, ry2),
                (rx1, ry2, rx1, ry1),
            ]
            any_clipped = False
            result = []
            for ex1, ey1, ex2, ey2 in edges:
                clipped, segs = _clip_segment_outside_circle(ex1, ey1, ex2, ey2, cx, cy, eff_r)
                any_clipped = any_clipped or clipped
                for sx1, sy1, sx2, sy2, _ in segs:
                    s = Stroke(
                        id=str(uuid.uuid4()),
                        tool="line",
                        colour=self.colour,
                        width=self.width,
                        opacity=self.opacity,
                        start_time=self.start_time,
                        end_time=self.end_time,
                    )
                    s.add_point(sx1, sy1, 1.0)
                    s.add_point(sx2, sy2, 1.0)
                    result.append(s)
            if not any_clipped:
                return False, [self]
            return True, result

        # 3. Freehand stroke (pen / highlighter): subdivide long segments near eraser & split
        eff_r2 = eff_r * eff_r
        if len(self.points) == 1:
            p = self.points[0]
            if (p.x - cx) ** 2 + (p.y - cy) ** 2 <= eff_r2:
                return True, []
            return False, [self]

        dense_pts: List[Point] = [self.points[0]]
        step_size = 2.5
        for i in range(len(self.points) - 1):
            pa = self.points[i]
            pb = self.points[i + 1]
            dx = pb.x - pa.x
            dy = pb.y - pa.y
            dist = math.hypot(dx, dy)
            # Subdivide segment if it is longer than step_size and near the eraser circle
            mid_x = (pa.x + pb.x) * 0.5
            mid_y = (pa.y + pb.y) * 0.5
            if dist > step_size and math.hypot(mid_x - cx, mid_y - cy) <= eff_r + dist:
                steps = max(2, int(math.ceil(dist / step_size)))
                for k in range(1, steps):
                    t = k / steps
                    dense_pts.append(
                        Point(
                            x=pa.x + t * dx,
                            y=pa.y + t * dy,
                            pressure=pa.pressure + t * (pb.pressure - pa.pressure),
                            timestamp=pa.timestamp,
                        )
                    )
            dense_pts.append(pb)

        runs: List[List[Point]] = []
        current_run: List[Point] = []
        removed_any = False

        for pt in dense_pts:
            if (pt.x - cx) ** 2 + (pt.y - cy) ** 2 <= eff_r2:
                removed_any = True
                if current_run:
                    runs.append(current_run)
                    current_run = []
            else:
                current_run.append(pt)
        if current_run:
            runs.append(current_run)

        if not removed_any:
            return False, [self]

        surviving: List[Stroke] = []
        for run in runs:
            if not run:
                continue
            s = Stroke(
                id=str(uuid.uuid4()),
                tool=self.tool,
                colour=self.colour,
                width=self.width,
                opacity=self.opacity,
                points=run,
                start_time=self.start_time,
                end_time=self.end_time,
            )
            surviving.append(s)
        return True, surviving

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
