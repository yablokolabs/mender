"""Layout checks for the README architecture diagram.

The diagram is drawn in `assets/arch-diagram.svg` and shipped as a PNG made by
`rsvg-convert`. Each label is measured with that same renderer, so these checks see the
text widths that a reader of the README sees.
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SVG_PATH = ASSETS / "arch-diagram.svg"
PNG_PATH = ASSETS / "arch-diagram.png"
SVG_NS = "http://www.w3.org/2000/svg"

# Labels are exported at this zoom so that a width is known to a quarter of a unit.
MEASURE_ZOOM = 4
# Share of the font size that glyphs reach above and below the text baseline.
ASCENT = 0.75
DESCENT = 0.22
CANVAS_MARGIN = 8.0
PADDING_X = 6.0
PADDING_Y = 3.0
TOLERANCE = 0.5

# CI installs the renderer, so a missing renderer there is a failure, not a skip.
pytestmark = pytest.mark.skipif(
    shutil.which("rsvg-convert") is None and "CI" not in os.environ,
    reason="rsvg-convert (package librsvg2-bin) is not installed",
)

Point = tuple[float, float]
Segment = tuple[Point, Point]


@dataclass(frozen=True)
class Box:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def area(self) -> float:
        return (self.right - self.left) * (self.bottom - self.top)

    def inset(self, dx: float, dy: float) -> Box:
        return Box(self.left + dx, self.top + dy, self.right - dx, self.bottom - dy)

    def holds_point(self, point: Point) -> bool:
        return self.left <= point[0] <= self.right and self.top <= point[1] <= self.bottom

    def holds(self, other: Box) -> bool:
        return (
            self.left - TOLERANCE <= other.left
            and self.top - TOLERANCE <= other.top
            and other.right <= self.right + TOLERANCE
            and other.bottom <= self.bottom + TOLERANCE
        )

    def overlaps(self, other: Box) -> bool:
        return (
            self.left + TOLERANCE < other.right
            and other.left + TOLERANCE < self.right
            and self.top + TOLERANCE < other.bottom
            and other.top + TOLERANCE < self.bottom
        )

    def __str__(self) -> str:
        return f"[{self.left:g},{self.top:g} to {self.right:g},{self.bottom:g}]"


@dataclass(frozen=True)
class Label:
    text: str
    anchor: Point
    extent: Box


@dataclass(frozen=True)
class Diagram:
    canvas: Box
    boxes: list[Box]
    labels: list[Label]
    connectors: list[Segment]

    def holder(self, label: Label) -> Box | None:
        """The smallest box that the label is anchored in."""
        holders = [box for box in self.boxes if box.holds_point(label.anchor)]
        return min(holders, key=lambda box: box.area, default=None)

    def leaf_boxes(self) -> list[Box]:
        """Boxes that hold no other box. Connectors can enter a panel, but not a leaf."""
        return [
            box
            for box in self.boxes
            if not any(other != box and box.holds(other) for other in self.boxes)
        ]


def _png_size(path: Path) -> tuple[int, int]:
    width, height = struct.unpack(">II", path.read_bytes()[16:24])
    return int(width), int(height)


def _render(svg: Path, out: Path, *args: str) -> tuple[int, int]:
    subprocess.run(["rsvg-convert", *args, "-o", str(out), str(svg)], check=True)
    return _png_size(out)


def _number(element: ET.Element, name: str) -> float:
    return float(element.get(name, "0"))


def _length_inside(segment: Segment, box: Box) -> float:
    """Length of the part of `segment` that lies inside `box` (Liang-Barsky clipping)."""
    (x1, y1), (x2, y2) = segment
    dx, dy = x2 - x1, y2 - y1
    enter, leave = 0.0, 1.0
    for direction, distance in (
        (-dx, x1 - box.left),
        (dx, box.right - x1),
        (-dy, y1 - box.top),
        (dy, box.bottom - y1),
    ):
        if direction == 0:
            if distance < 0:
                return 0.0
            continue
        ratio = distance / direction
        if direction < 0:
            enter = max(enter, ratio)
        else:
            leave = min(leave, ratio)
    if enter >= leave:
        return 0.0
    return (leave - enter) * math.hypot(dx, dy)


@pytest.fixture(scope="module")
def diagram(tmp_path_factory: pytest.TempPathFactory) -> Diagram:
    assert SVG_PATH.is_file(), f"diagram source is missing: {SVG_PATH}"
    work = tmp_path_factory.mktemp("arch-diagram")
    ET.register_namespace("", SVG_NS)
    tree = ET.parse(SVG_PATH)
    root = tree.getroot()

    view = [float(value) for value in root.get("viewBox", "").replace(",", " ").split()]
    assert len(view) == 4, "the <svg> element needs a viewBox"
    canvas = Box(view[0], view[1], view[0] + view[2], view[1] + view[3])

    boxes: list[Box] = []
    connectors: list[Segment] = []
    texts: list[tuple[ET.Element, dict[str, str]]] = []

    def walk(element: ET.Element, inherited: dict[str, str]) -> None:
        tag = element.tag.removeprefix(f"{{{SVG_NS}}}")
        if tag == "defs":
            return
        assert element.get("transform") is None, (
            f"<{tag}> uses a transform; this check reads coordinates as written"
        )
        style = {
            name: element.get(name, inherited.get(name, default))
            for name, default in (("font-size", ""), ("text-anchor", "start"))
        }
        if tag == "rect":
            x, y = _number(element, "x"), _number(element, "y")
            boxes.append(Box(x, y, x + _number(element, "width"), y + _number(element, "height")))
        elif tag == "text" and "".join(element.itertext()).strip():
            texts.append((element, style))
        elif tag == "line":
            connectors.append(
                (
                    (_number(element, "x1"), _number(element, "y1")),
                    (_number(element, "x2"), _number(element, "y2")),
                )
            )
        else:
            assert tag not in {"path", "polyline"}, (
                f"<{tag}> is not read by this check; draw each connector as a <line>"
            )
        for child in element:
            walk(child, style)

    walk(root, {})

    for number, (element, _) in enumerate(texts):
        element.set("id", f"measured-label-{number}")
    measured = work / "measured.svg"
    tree.write(measured, encoding="utf-8", xml_declaration=True)
    full_width, _ = _render(measured, work / "full.png")
    pixels_per_unit = full_width / (canvas.right - canvas.left) * MEASURE_ZOOM

    labels: list[Label] = []
    for number, (element, style) in enumerate(texts):
        text = " ".join("".join(element.itertext()).split())
        assert style["font-size"], f"label {text!r} needs a font-size attribute"
        size = float(style["font-size"])
        pixel_width, _ = _render(
            measured,
            work / "label.png",
            "--zoom",
            str(MEASURE_ZOOM),
            f"--export-id=measured-label-{number}",
        )
        width = pixel_width / pixels_per_unit
        x, y = _number(element, "x"), _number(element, "y")
        left = {"start": x, "middle": x - width / 2, "end": x - width}[style["text-anchor"]]
        labels.append(
            Label(
                text=text,
                anchor=(x, y - 0.3 * size),
                extent=Box(left, y - ASCENT * size, left + width, y + DESCENT * size),
            )
        )
    return Diagram(canvas=canvas, boxes=boxes, labels=labels, connectors=connectors)


def test_nothing_is_outside_the_canvas(diagram: Diagram) -> None:
    assert any(box.holds(diagram.canvas) for box in diagram.boxes), (
        "no background box covers the whole canvas, so part of the PNG is transparent"
    )
    outside = [f"box {box}" for box in diagram.boxes if not diagram.canvas.holds(box)]
    safe_area = diagram.canvas.inset(CANVAS_MARGIN, CANVAS_MARGIN)
    outside += [
        f"label {label.text!r} {label.extent}"
        for label in diagram.labels
        if not safe_area.holds(label.extent)
    ]
    assert not outside, "outside the canvas:\n" + "\n".join(outside)


def test_each_label_fits_inside_the_box_that_holds_it(diagram: Diagram) -> None:
    problems: list[str] = []
    for label in diagram.labels:
        holder = diagram.holder(label)
        if holder is None:
            problems.append(f"{label.text!r} is not on any box")
        elif not holder.inset(PADDING_X, PADDING_Y).holds(label.extent):
            overflow = max(
                label.extent.right - (holder.right - PADDING_X),
                (holder.left + PADDING_X) - label.extent.left,
                label.extent.bottom - (holder.bottom - PADDING_Y),
                (holder.top + PADDING_Y) - label.extent.top,
            )
            problems.append(f"{label.text!r} overflows box {holder} by {overflow:.1f}")
    assert not problems, "labels that do not fit:\n" + "\n".join(problems)


def test_labels_do_not_overlap_other_labels_or_other_boxes(diagram: Diagram) -> None:
    problems = [
        f"{first.text!r} overlaps {second.text!r}"
        for first, second in combinations(diagram.labels, 2)
        if first.extent.overlaps(second.extent)
    ]
    problems += [
        f"{label.text!r} lies on box {box}"
        for label in diagram.labels
        for box in diagram.boxes
        if not box.holds_point(label.anchor) and box.overlaps(label.extent)
    ]
    assert not problems, "overlapping labels:\n" + "\n".join(problems)


def test_boxes_are_nested_or_apart(diagram: Diagram) -> None:
    problems = [
        f"box {first} partly overlaps box {second}"
        for first, second in combinations(diagram.boxes, 2)
        if first.overlaps(second) and not first.holds(second) and not second.holds(first)
    ]
    assert not problems, "\n".join(problems)


def test_connectors_do_not_cross_boxes_or_labels(diagram: Diagram) -> None:
    obstacles = [(f"box {box}", box.inset(1.0, 1.0)) for box in diagram.leaf_boxes()]
    obstacles += [(f"label {label.text!r}", label.extent) for label in diagram.labels]
    problems = sorted(
        {
            f"connector {start} to {end} crosses {name}"
            for start, end in diagram.connectors
            for name, area in obstacles
            if _length_inside((start, end), area) > TOLERANCE
        }
    )
    assert not problems, "\n".join(problems)


def test_the_png_shows_the_whole_canvas(diagram: Diagram) -> None:
    width, height = _png_size(PNG_PATH)
    canvas_ratio = (diagram.canvas.right - diagram.canvas.left) / (
        diagram.canvas.bottom - diagram.canvas.top
    )
    assert width >= 1600, "the README image must stay sharp on a high-density display"
    assert width / height == pytest.approx(canvas_ratio, rel=0.005), (
        "assets/arch-diagram.png does not have the shape of the SVG canvas; run `make diagram`"
    )
