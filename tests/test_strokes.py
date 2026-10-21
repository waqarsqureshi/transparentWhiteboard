from canvas.stroke import Point, Stroke

def test_point_creation_and_serialization():
    pt = Point(x=150.5, y=200.75, pressure=0.85)
    data = pt.to_dict()
    assert data["x"] == 150.5
    assert data["y"] == 200.75
    assert data["pressure"] == 0.85
    restored = Point.from_dict(data)
    assert restored.x == 150.5
    assert restored.y == 200.75

def test_stroke_add_point_and_bounding_box():
    stroke = Stroke(id="test-1", tool="pen", colour="#FF0000", width=4.0)
    stroke.add_point(100, 100, pressure=0.5)
    stroke.add_point(200, 250, pressure=0.9)
    assert len(stroke.points) == 2
    min_x, min_y, max_x, max_y = stroke.bounding_box()
    assert min_x < 100
    assert max_x > 200

def test_rectangle_and_arrow_strokes():
    # Arrow stroke
    arrow = Stroke(id="arrow-1", tool="arrow", colour="#007AFF", width=4.0)
    arrow.add_point(50, 50)
    arrow.add_point(150, 50)
    assert arrow.intersects_point(100, 50, tolerance=5.0)
    assert not arrow.intersects_point(100, 100, tolerance=5.0)

    # Rectangle stroke
    rect = Stroke(id="rect-1", tool="rectangle", colour="#34C759", width=4.0)
    rect.add_point(10, 10)
    rect.add_point(110, 110)
    # Point on top edge
    assert rect.intersects_point(60, 10, tolerance=5.0)
    # Point on right edge
    assert rect.intersects_point(110, 60, tolerance=5.0)
    # Point far outside
    assert not rect.intersects_point(200, 200, tolerance=5.0)


def test_physical_rubber_partial_erase_pen_and_line():
    # Freehand pen stroke from x=0 to x=200 along y=50
    s = Stroke(id="pen-1", tool="pen", colour="#FF3B30", width=4.0)
    for x in range(0, 201, 10):
        s.add_point(float(x), 50.0)

    changed, pieces = s.erase_circle(100.0, 50.0, 20.0)
    assert changed is True
    assert len(pieces) == 2
    # Left piece ends around x=80, right piece starts around x=120
    assert pieces[0].points[-1].x <= 81.0
    assert pieces[1].points[0].x >= 119.0

    # Straight 2-point line erased in the middle splits into 2 lines
    line = Stroke(id="line-1", tool="line", colour="#007AFF", width=4.0)
    line.add_point(0.0, 100.0)
    line.add_point(200.0, 100.0)
    changed_l, pieces_l = line.erase_circle(100.0, 100.0, 15.0)
    assert changed_l is True
    assert len(pieces_l) == 2
    assert all(p.tool == "line" for p in pieces_l)


def test_physical_rubber_partial_erase_arrow_and_rectangle():
    # Arrow erased in the shaft keeps the arrowhead on the tip segment
    arrow = Stroke(id="arrow-2", tool="arrow", colour="#FF9500", width=4.0)
    arrow.add_point(0.0, 50.0)
    arrow.add_point(200.0, 50.0)
    changed_a, pieces_a = arrow.erase_circle(80.0, 50.0, 15.0)
    assert changed_a is True
    assert len(pieces_a) == 2
    assert pieces_a[0].tool == "line"
    assert pieces_a[1].tool == "arrow"

    # Rectangle erased on top edge decomposes into clipped edges
    rect = Stroke(id="rect-2", tool="rectangle", colour="#34C759", width=4.0)
    rect.add_point(0.0, 0.0)
    rect.add_point(100.0, 100.0)
    changed_r, pieces_r = rect.erase_circle(50.0, 0.0, 15.0)
    assert changed_r is True
    assert len(pieces_r) == 5  # top edge split into 2 + 3 intact edges
