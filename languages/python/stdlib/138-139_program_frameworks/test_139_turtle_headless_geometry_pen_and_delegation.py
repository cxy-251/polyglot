"""139｜turtle：无窗口的几何、画笔状态与默认对象委派。

turtle 的真实画布由 tkinter 提供，通常需要显示服务器。
本套案例专注于同一个模块内可确定验证的核心机制：向量、导航、画笔、
形状、撤销缓冲、配置和面向过程 API 的单例委派。记录型教学对象组合
``TNavigator`` 与 ``TPen``，用线段列表代替 GUI 画布，仍然展示
“移动时是否落笔”的真实协议。

若容器没有可导入的 tkinter，pytest 会跳过本文件；它不会尝试安装依赖或
打开窗口。这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.turtle python.turtle.tkinter-dependency
# polyglot-covers: python.turtle.Vec2D-tuple-protocol
# polyglot-covers: python.turtle.Vec2D-vector-arithmetic
# polyglot-covers: python.turtle.Vec2D-inner-product-norm-rotate
# polyglot-covers: python.turtle.Vec2D-pickle-and-repr
# polyglot-covers: python.turtle.TNavigator-standard-navigation
# polyglot-covers: python.turtle.TNavigator-goto-coordinate-overloads
# polyglot-covers: python.turtle.TNavigator-distance-and-towards
# polyglot-covers: python.turtle.TNavigator-degree-radian-custom-units
# polyglot-covers: python.turtle.TNavigator-standard-world-logo-modes
# polyglot-covers: python.turtle.TNavigator-circle-polygon-approximation
# polyglot-covers: python.turtle.TNavigator-method-aliases
# polyglot-covers: python.turtle.TPen-state-dictionary
# polyglot-covers: python.turtle.TPen-penup-pendown-visibility
# polyglot-covers: python.turtle.TPen-pensize-speed-resizemode
# polyglot-covers: python.turtle.TPen-color-input-forms
# polyglot-covers: python.turtle.TPen-new-line-before-state-change
# polyglot-covers: python.turtle.TPen-shape-transform
# polyglot-covers: python.turtle.Shape-polygon-image-compound
# polyglot-covers: python.turtle.Tbuffer-ring-and-cumulative-action
# polyglot-covers: python.turtle.config-dict-typed-values-and-errors
# polyglot-covers: python.turtle.TurtleScreen-colormode-and-rgb-conversion
# polyglot-covers: python.turtle.TurtleScreen-register-shape
# polyglot-covers: python.turtle.procedural-api-default-pen-and-screen
# polyglot-covers: python.turtle.Terminator-running-guard
# polyglot-covers: python.turtle.write-docstring-dict

import math
import pickle

import pytest


turtle = pytest.importorskip(
    "turtle",
    reason="turtle 的标准库实现依赖可导入的 tkinter",
)


class RecordingPen(turtle.TPen):
    """为 TPen 的四个绘图钩子提供最小可观察实现。"""

    def __init__(self, *args, **kwargs):
        self.operations = []
        super().__init__(*args, **kwargs)

    def _newLine(self, usePos=True):
        self.operations.append(
            (
                "new-line",
                usePos,
                self._drawing,
                self._pencolor,
                self._pensize,
            )
        )

    def _update(self, count=True, forced=False):
        self.operations.append(("update", count, forced))

    def _color(self, value):
        return value

    def _colorstr(self, args):
        if isinstance(args, str):
            return args
        if len(args) == 1:
            value = args[0]
            if isinstance(value, str):
                return value
        else:
            value = args
        try:
            red, green, blue = value
        except (TypeError, ValueError) as error:
            raise turtle.TurtleGraphicsError("bad teaching color") from error
        return f"#{red:02x}{green:02x}{blue:02x}"


class RecordingTurtle(turtle.TPen, turtle.TNavigator):
    """组合 turtle 的导航和画笔 mixin，以记录线段代替画布绘制。"""

    def __init__(self, mode="standard"):
        self.segments = []
        self.operations = []
        turtle.TNavigator.__init__(self, mode)
        turtle.TPen.__init__(self)

    def _goto(self, end):
        start = self._position
        if self._drawing:
            self.segments.append((start, end, self._pencolor, self._pensize))
        self._position = end

    def _newLine(self, usePos=True):
        self.operations.append(("new-line", usePos))

    def _update(self, count=True, forced=False):
        self.operations.append(("update", count, forced))

    def _color(self, value):
        return value

    def _colorstr(self, args):
        if isinstance(args, str):
            return args
        if len(args) == 1:
            return args[0]
        return args


class FakeProceduralPen:
    def __init__(self):
        self.calls = []

    def forward(self, distance):
        self.calls.append(("forward", distance))
        return "moved"

    def fd(self, distance):
        self.calls.append(("fd", distance))
        return "alias-moved"

    def pos(self):
        self.calls.append(("pos",))
        return turtle.Vec2D(3, 4)


class FakeProceduralScreen:
    def __init__(self):
        self.calls = []

    def bgcolor(self, *args):
        self.calls.append(("bgcolor", args))
        return "navy"

    def mode(self, value=None):
        self.calls.append(("mode", value))
        return value or "standard"


def assert_vector_close(actual, expected):
    assert tuple(actual) == pytest.approx(tuple(expected))


def test_vec2d_is_an_immutable_tuple_with_teaching_repr_and_hash():
    vector = turtle.Vec2D(0.567, 1.234)

    assert isinstance(vector, tuple)
    assert tuple(vector) == (0.567, 1.234)
    assert vector == (0.567, 1.234)
    assert repr(vector) == "(0.57,1.23)"
    assert {vector: "point"}[turtle.Vec2D(0.567, 1.234)] == "point"

    with pytest.raises(TypeError):
        turtle.Vec2D((1, 2))
    with pytest.raises(TypeError):
        vector[0] = 9


def test_vec2d_add_subtract_negate_and_scalar_multiplication():
    first = turtle.Vec2D(3, -2)
    second = turtle.Vec2D(0.5, 4)

    assert_vector_close(first + second, (3.5, 2))
    assert_vector_close(first - second, (2.5, -6))
    assert_vector_close(-first, (-3, 2))
    assert_vector_close(first * 2, (6, -4))
    assert_vector_close(2.5 * first, (7.5, -5))


def test_vec2d_multiplication_dispatches_vector_to_inner_product():
    first = turtle.Vec2D(3, 4)
    second = turtle.Vec2D(-2, 5)

    assert first * second == 14
    assert abs(first) == 5
    # 同一个 ``*`` 遇到 Vec2D 返回标量，遇到数字才返回缩放后的向量。
    assert isinstance(first * second, (int, float))
    assert isinstance(first * 2, turtle.Vec2D)


@pytest.mark.parametrize(
    ("vector", "angle", "expected"),
    [
        ((1, 0), 90, (0, 1)),
        ((0, 1), -90, (1, 0)),
        ((1, 0), 180, (-1, 0)),
        ((2, -3), 360, (2, -3)),
    ],
)
def test_vec2d_rotate_uses_counterclockwise_degrees(vector, angle, expected):
    result = turtle.Vec2D(*vector).rotate(angle)
    assert_vector_close(result, expected)


def test_vec2d_pickle_uses_newargs_to_preserve_subclass():
    vector = turtle.Vec2D(0.5, 2)

    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        restored = pickle.loads(pickle.dumps(vector, protocol=protocol))
        assert restored == vector
        assert isinstance(restored, turtle.Vec2D)


def test_standard_navigation_moves_in_current_orientation_and_wraps_heading():
    navigator = turtle.TNavigator()

    navigator.forward(100)
    navigator.left(90)
    navigator.forward(25)
    navigator.right(450)
    navigator.back(10)

    assert_vector_close(navigator.pos(), (90, 25))
    assert navigator.heading() == pytest.approx(0)
    assert navigator.xcor() == pytest.approx(90)
    assert navigator.ycor() == pytest.approx(25)


def test_navigation_aliases_are_the_same_class_level_functions():
    navigator = turtle.TNavigator()

    assert navigator.fd.__func__ is navigator.forward.__func__
    assert navigator.bk.__func__ is navigator.back.__func__
    assert navigator.backward.__func__ is navigator.back.__func__
    assert navigator.rt.__func__ is navigator.right.__func__
    assert navigator.lt.__func__ is navigator.left.__func__
    assert navigator.position.__func__ is navigator.pos.__func__
    assert navigator.setpos.__func__ is navigator.goto.__func__
    assert navigator.seth.__func__ is navigator.setheading.__func__


def test_goto_accepts_xy_pair_vector_and_other_navigator():
    navigator = turtle.TNavigator()
    other = turtle.TNavigator()
    other.goto(9, 10)

    navigator.goto(1, 2)
    assert_vector_close(navigator.pos(), (1, 2))
    navigator.goto((3, 4))
    assert_vector_close(navigator.pos(), (3, 4))
    navigator.goto(turtle.Vec2D(5, 6))
    assert_vector_close(navigator.pos(), (5, 6))
    navigator.goto(other)
    assert_vector_close(navigator.pos(), (9, 10))


def test_set_coordinates_home_and_reset_preserve_or_restore_expected_state():
    navigator = turtle.TNavigator()
    navigator.goto(10, 20)
    navigator.left(45)

    navigator.setx(-5)
    assert_vector_close(navigator.pos(), (-5, 20))
    navigator.sety(8)
    assert_vector_close(navigator.pos(), (-5, 8))
    assert navigator.heading() == pytest.approx(45)

    navigator.home()
    assert_vector_close(navigator.pos(), (0, 0))
    assert navigator.heading() == pytest.approx(0)


def test_distance_accepts_coordinates_pairs_vectors_and_navigators():
    navigator = turtle.TNavigator()
    other = turtle.TNavigator()
    other.goto(6, 8)

    assert navigator.distance(3, 4) == pytest.approx(5)
    assert navigator.distance((6, 8)) == pytest.approx(10)
    assert navigator.distance(turtle.Vec2D(5, 12)) == pytest.approx(13)
    assert navigator.distance(other) == pytest.approx(10)


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ((1, 0), 0),
        ((1, 1), 45),
        ((0, 1), 90),
        ((-1, 0), 180),
        ((0, -1), 270),
    ],
)
def test_towards_reports_absolute_heading_without_turning(target, expected):
    navigator = turtle.TNavigator()
    navigator.left(30)

    assert navigator.towards(target) == pytest.approx(expected)
    assert navigator.heading() == pytest.approx(30)


def test_degrees_radians_and_custom_fullcircle_change_angle_units_only():
    navigator = turtle.TNavigator()
    navigator.left(90)

    assert navigator.heading() == pytest.approx(90)
    navigator.radians()
    assert navigator.heading() == pytest.approx(math.pi / 2)
    navigator.degrees(400)
    assert navigator.heading() == pytest.approx(100)
    navigator.setheading(250)
    assert navigator.heading() == pytest.approx(250)


def test_logo_mode_changes_zero_direction_and_clockwise_angle_orientation():
    standard = turtle.TNavigator("standard")
    world = turtle.TNavigator("world")
    logo = turtle.TNavigator("logo")

    standard.forward(10)
    world.forward(10)
    logo.forward(10)
    assert_vector_close(standard.pos(), (10, 0))
    assert_vector_close(world.pos(), (10, 0))
    assert_vector_close(logo.pos(), (0, 10))

    logo.right(90)
    logo.forward(5)
    assert logo.heading() == pytest.approx(90)
    assert_vector_close(logo.pos(), (5, 10))


def test_invalid_navigation_mode_is_ignored_without_changing_current_mode():
    navigator = turtle.TNavigator("standard")

    assert navigator._setmode() == "standard"
    assert navigator._setmode("diagonal") is None
    assert navigator._setmode() == "standard"


def test_circle_approximates_arc_with_steps_and_changes_heading_by_extent():
    navigator = turtle.TNavigator()

    navigator.circle(50, extent=180, steps=4)

    assert_vector_close(navigator.pos(), (0, 100))
    assert navigator.heading() == pytest.approx(180)


def test_recording_turtle_connects_navigation_to_pen_down_state():
    pen = RecordingTurtle()

    pen.forward(10)
    pen.penup()
    pen.goto(20, 5)
    pen.pendown()
    pen.sety(15)

    assert [(tuple(start), tuple(end)) for start, end, _, _ in pen.segments] == [
        ((0, 0), (10, 0)),
        ((20, 5), (20, 15)),
    ]
    assert_vector_close(pen.pos(), (20, 15))


def test_tpen_default_state_and_visibility_drawing_aliases():
    pen = RecordingPen()

    assert pen.isdown() is True
    assert pen.isvisible() is True
    pen.up()
    pen.ht()
    assert pen.isdown() is False
    assert pen.isvisible() is False
    pen.pd()
    pen.st()
    assert pen.isdown() is True
    assert pen.isvisible() is True
    assert pen.width.__func__ is pen.pensize.__func__


def test_pen_returns_snapshot_and_restores_multiple_attributes_together():
    pen = RecordingPen()
    initial = pen.pen()

    pen.pen(
        pendown=False,
        pencolor="red",
        fillcolor="blue",
        pensize=5,
        shown=False,
    )
    changed = pen.pen()
    assert changed["pendown"] is False
    assert changed["pencolor"] == "red"
    assert changed["fillcolor"] == "blue"
    assert changed["pensize"] == 5
    assert changed["shown"] is False

    pen.pen(initial)
    assert pen.pen() == initial


def test_pen_starts_one_new_line_before_line_affecting_state_changes():
    pen = RecordingPen()
    pen.operations.clear()

    pen.pen(pendown=False, pencolor="red", pensize=4, fillcolor="blue")

    assert pen.operations[0] == (
        "new-line",
        True,
        True,
        "black",
        1,
    )
    assert [event[0] for event in pen.operations] == ["new-line", "update"]


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("fastest", 0),
        ("fast", 10),
        ("normal", 6),
        ("slow", 3),
        ("slowest", 1),
        (4.6, 5),
        (99, 0),
        (-1, 0),
    ],
)
def test_speed_maps_names_rounds_in_range_and_uses_zero_outside(given, expected):
    pen = RecordingPen()

    pen.speed(given)

    assert pen.speed() == expected


def test_pensize_and_resizemode_query_set_and_ignore_unknown_mode():
    pen = RecordingPen(resizemode="noresize")

    assert pen.pensize() == 1
    pen.pensize(7)
    assert pen.pensize() == 7
    assert pen.resizemode() == "noresize"
    pen.resizemode("AUTO")
    assert pen.resizemode() == "auto"
    pen.resizemode("stretch-everything")
    assert pen.resizemode() == "auto"


def test_color_supports_shared_separate_and_rgb_inputs():
    pen = RecordingPen()

    pen.color("red")
    assert pen.color() == ("red", "red")
    pen.color("navy", "gold")
    assert pen.color() == ("navy", "gold")
    pen.color(1, 2, 3)
    assert pen.color() == ("#010203", "#010203")
    pen.pencolor((10, 20, 30))
    pen.fillcolor(40, 50, 60)
    assert pen.color() == ("#0a141e", "#28323c")


def test_pen_shape_transform_combines_stretch_shear_and_radian_tilt():
    pen = RecordingPen()

    pen.pen(stretchfactor=(2, 3), shearfactor=0.5, tilt=math.pi / 2)

    assert pen.pen()["stretchfactor"] == (2, 3)
    assert pen.pen()["shearfactor"] == 0.5
    assert pen.pen()["tilt"] == pytest.approx(math.pi / 2)
    assert pen._shapetrafo == pytest.approx((0, 3, -2, -1.5))


def test_pen_rejects_unknown_state_key_before_mutating_state():
    pen = RecordingPen()
    before = pen.pen()

    with pytest.raises(KeyError, match="unknown"):
        pen.pen(unknown="value")

    assert pen.pen() == before


def test_shape_normalizes_polygon_list_and_builds_compound_components():
    points = [(0, 0), (10, 0), (0, 10)]
    polygon = turtle.Shape("polygon", points)
    assert polygon._type == "polygon"
    assert polygon._data == tuple(points)

    compound = turtle.Shape("compound")
    compound.addcomponent(tuple(points), "red")
    compound.addcomponent(tuple(reversed(points)), "blue", "black")
    assert compound._data == [
        [tuple(points), "red", "red"],
        [tuple(reversed(points)), "blue", "black"],
    ]


def test_shape_rejects_unknown_type_and_component_on_noncompound_shape():
    with pytest.raises(turtle.TurtleGraphicsError, match="no shape type"):
        turtle.Shape("mesh")

    polygon = turtle.Shape("polygon", ((0, 0), (1, 0), (0, 1)))
    with pytest.raises(turtle.TurtleGraphicsError, match="Cannot add component"):
        polygon.addcomponent(((0, 0),), "red")


def test_image_shape_keeps_nonexistent_gif_name_without_loading_tk_image(tmp_path):
    missing = str(tmp_path / "missing.gif")

    shape = turtle.Shape("image", missing)

    assert shape._type == "image"
    assert shape._data == missing


def test_tbuffer_is_bounded_and_pops_newest_actions_first():
    buffer = turtle.Tbuffer(2)

    buffer.push(("first",))
    buffer.push(("second",))
    buffer.push(("third",))

    assert buffer.nr_of_items() == 2
    assert buffer.pop() == ("third",)
    assert buffer.pop() == ("second",)
    assert buffer.nr_of_items() == 0


def test_tbuffer_cumulate_groups_subactions_into_one_undo_entry():
    buffer = turtle.Tbuffer(5)
    buffer.push(["sequence"])
    buffer.cumulate = True
    buffer.push(("move", 10))
    buffer.push(("turn", 90))
    buffer.cumulate = False

    assert buffer.nr_of_items() == 1
    assert buffer.pop() == [
        "sequence",
        ("move", 10),
        ("turn", 90),
    ]


def test_tbuffer_reset_can_keep_or_replace_capacity():
    buffer = turtle.Tbuffer(2)
    buffer.push(("move",))
    buffer.reset()
    assert buffer.bufsize == 2
    assert buffer.nr_of_items() == 0

    buffer.reset(4)
    assert buffer.bufsize == 4
    assert buffer.nr_of_items() == 0
    assert buffer.ptr == -1


def test_rawturtle_undo_buffer_can_be_enabled_resized_or_disabled_headlessly():
    raw = object.__new__(turtle.RawTurtle)
    raw.undobuffer = None

    raw.setundobuffer(3)
    assert isinstance(raw.undobuffer, turtle.Tbuffer)
    raw.undobuffer.push(("move",))
    assert raw.undobufferentries() == 1
    raw.setundobuffer(0)
    assert raw.undobuffer is None
    assert raw.undobufferentries() == 0


def test_config_dict_converts_supported_literals_numbers_and_strings(tmp_path):
    config = tmp_path / "turtle.cfg"
    config.write_text(
        """
        # 空行和注释会忽略
        width = 0.75
        canvwidth = 500
        visible = False
        leftright = None
        using_IDLE = ''
        pencolor = dark green
        """,
        encoding="utf-8",
    )

    assert turtle.config_dict(config) == {
        "width": 0.75,
        "canvwidth": 500,
        "visible": False,
        "leftright": None,
        "using_IDLE": "",
        "pencolor": "dark green",
    }


def test_config_dict_reports_bad_lines_and_keeps_valid_neighbors(tmp_path, capsys):
    config = tmp_path / "broken.cfg"
    config.write_text(
        "pencolor = red\nfillcolor: blue\nvisible = True\n",
        encoding="utf-8",
    )

    parsed = turtle.config_dict(config)

    assert parsed == {"pencolor": "red", "visible": True}
    output = capsys.readouterr().out
    assert f"Bad line in config-file {config}" in output
    assert "fillcolor: blue" in output


def make_headless_screen(colormode=1.0):
    screen = object.__new__(turtle.TurtleScreen)
    screen._colormode = colormode
    screen._shapes = {}
    return screen


def test_turtlescreen_rgb_conversion_obeys_colormode_and_hex_roundtrip():
    screen = make_headless_screen(1.0)

    assert screen._colorstr((0.5, 0, 1.0)) == "#8000ff"
    assert screen._color("#ff0080") == pytest.approx((1.0, 0.0, 128 / 255))

    screen.colormode(255)
    assert screen.colormode() == 255
    assert screen._colorstr((128, 0, 255)) == "#8000ff"
    assert screen._color("#f08") == pytest.approx((240, 0, 128))


def test_turtlescreen_rejects_bad_rgb_and_silently_ignores_invalid_colormode():
    screen = make_headless_screen(1.0)

    with pytest.raises(turtle.TurtleGraphicsError, match="bad color sequence"):
        screen._colorstr((1.1, 0, 0))
    with pytest.raises(turtle.TurtleGraphicsError, match="bad color arguments"):
        screen._colorstr((1, 2))

    screen.colormode(100)
    assert screen.colormode() == 1.0


def test_turtlescreen_registers_polygon_and_compound_shapes_without_canvas():
    screen = make_headless_screen()
    triangle = ((0, 0), (10, 0), (0, 10))
    compound = turtle.Shape("compound")
    compound.addcomponent(triangle, "red")

    screen.register_shape("triangle", triangle)
    screen.register_shape("badge", compound)

    assert isinstance(screen._shapes["triangle"], turtle.Shape)
    assert screen._shapes["triangle"]._data == triangle
    assert screen._shapes["badge"] is compound
    assert screen.getshapes() == ["badge", "triangle"]


def test_turtlescreen_register_shape_requires_gif_name_when_shape_is_omitted():
    screen = make_headless_screen()

    with pytest.raises(turtle.TurtleGraphicsError, match="Bad arguments"):
        screen.register_shape("not-an-image")


def test_procedural_functions_delegate_to_cached_default_pen_and_screen(monkeypatch):
    pen = FakeProceduralPen()
    screen = FakeProceduralScreen()
    monkeypatch.setattr(turtle.Turtle, "_pen", pen)
    monkeypatch.setattr(turtle.Turtle, "_screen", screen)

    assert turtle.forward(12) == "moved"
    assert turtle.fd(3) == "alias-moved"
    assert turtle.pos() == turtle.Vec2D(3, 4)
    assert turtle.bgcolor("navy") == "navy"
    assert turtle.mode("logo") == "logo"
    assert pen.calls == [
        ("forward", 12),
        ("fd", 3),
        ("pos",),
    ]
    assert screen.calls == [
        ("bgcolor", ("navy",)),
        ("mode", "logo"),
    ]


def test_procedural_function_raises_terminator_before_recreating_closed_screen(
    monkeypatch,
):
    monkeypatch.setattr(turtle.Turtle, "_pen", None)
    monkeypatch.setattr(turtle.TurtleScreen, "_RUNNING", False)

    with pytest.raises(turtle.Terminator):
        turtle.forward(1)

    # 守卫先恢复标志再抛异常；这条分支不会创建 Tk 窗口。
    assert turtle.TurtleScreen._RUNNING is True


def test_write_docstringdict_creates_importable_source_and_omits_aliases(tmp_path):
    target = tmp_path / "teaching_turtle_docs"

    turtle.write_docstringdict(str(target))

    generated = target.with_suffix(".py").read_text(encoding="utf-8")
    assert generated.startswith("docsdict = {")
    assert "'_Screen.bgcolor'" in generated
    assert "'Turtle.forward'" in generated
    # fd 等别名与原方法共用文档，生成器刻意只写规范名称。
    assert "'Turtle.fd'" not in generated
