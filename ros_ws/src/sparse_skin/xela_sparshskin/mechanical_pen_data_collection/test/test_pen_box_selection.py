import numpy as np

from mechanical_pen_data_collection.pen_box_selection import (
    box_iou,
    choose_consistent_box,
)


def rect(cx, cy, w, h):
    return np.array(
        [[cx - w / 2, cy - h / 2], [cx + w / 2, cy - h / 2],
         [cx + w / 2, cy + h / 2], [cx - w / 2, cy + h / 2]], dtype=np.float32,
    )


def test_iou():
    assert abs(box_iou(rect(0, 0, 10, 10), rect(0, 0, 10, 10)) - 1.0) < 1e-6
    assert abs(box_iou(rect(0, 0, 10, 10), rect(5, 0, 10, 10)) - 50 / 150) < 1e-6
    assert box_iou(rect(0, 0, 10, 10), rect(100, 0, 10, 10)) == 0.0


def test_reversed_winding():
    assert abs(box_iou(rect(0, 0, 10, 10), rect(0, 0, 10, 10)[::-1]) - 1.0) < 1e-6


def test_shrunken_boxes_are_ignored():
    # The pen at x=100 most of the time; a hand covers it for a while (much smaller boxes
    # that the most similar pick would otherwise favour, being many and alike).
    boxes = [rect(100 + d, 50, 200, 40) for d in (-2, 0, 1, 3, 0)]
    boxes += [rect(60, 50, 80, 40)] * 3
    choice = choose_consistent_box(boxes, scores=[0.9] * 5 + [0.99] * 3)
    assert choice.shrunken == 3
    assert choice.index in range(5)
    assert choice.index in (1, 4)  # at x=100: the middle of the others


def test_highest_similarity_beats_score():
    boxes = [rect(100, 50, 200, 40), rect(102, 50, 200, 40), rect(160, 60, 200, 40)]
    choice = choose_consistent_box(boxes, scores=[0.5, 0.6, 0.99])
    assert choice.index in (0, 1)


def test_tie_goes_to_higher_score():
    boxes = [rect(100, 50, 200, 40)] * 3
    choice = choose_consistent_box(boxes, scores=[0.5, 0.9, 0.7])
    assert choice.index == 1


def test_one_or_no_box():
    assert choose_consistent_box([]) is None
    assert choose_consistent_box([rect(0, 0, 10, 10)]).index == 0
