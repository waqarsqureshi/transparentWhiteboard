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
