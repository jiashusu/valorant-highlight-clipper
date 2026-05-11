from valorant_clipper.core import group_kill_frame_details, group_kill_frames, safe_stem
from pathlib import Path


def test_group_kill_frames_merges_nearby_ranges():
    result = group_kill_frames(
        [10, 11, 12, 40, 41, 42],
        framerate=10,
        seconds_before=0.5,
        seconds_after=0.2,
        merge_gap_seconds=3,
    )
    assert result == [(0.5, 4.4)]


def test_group_kill_frame_details_counts_merged_kills():
    result = group_kill_frame_details(
        [10, 11, 12, 40, 41, 42, 90, 91, 92],
        framerate=10,
        seconds_before=0.5,
        seconds_after=0.2,
        merge_gap_seconds=3,
    )
    assert [(item.start, item.end, item.kills) for item in result] == [
        (0.5, 4.4, 2),
        (8.5, 9.4, 1),
    ]


def test_group_kill_frame_details_filters_short_events():
    result = group_kill_frame_details(
        [10, 11, 12, 30, 31, 32, 33],
        framerate=10,
        seconds_before=0.5,
        seconds_after=0.2,
        merge_gap_seconds=0,
        min_event_seconds=0.4,
    )
    assert [(item.start, item.end, item.kills) for item in result] == [
        (2.5, 3.5, 1),
    ]


def test_safe_stem_keeps_readable_ascii():
    assert safe_stem(Path("Valorant 2026.05.11 - 01.16.27.01.mp4")) == "Valorant-2026-05-11---01-16-27-01"
