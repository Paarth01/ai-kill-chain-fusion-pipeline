"""
Tests for classification/yolo_detector.py's frame-source handling.

These are skipped automatically if the optional detection deps
(ultralytics/opencv, requirements-detection.txt) aren't installed —
they're not part of the fast default test path, same reasoning as why
those deps aren't in requirements.txt.
"""

import os

import pytest

pytest.importorskip("cv2")
pytest.importorskip("ultralytics")

import cv2  # noqa: E402

from backend.app.classification.yolo_detector import DetectorUnavailable, _get_frame  # noqa: E402
from backend.app.config import settings  # noqa: E402


@pytest.fixture
def demo_video_path(tmp_path):
    """Builds a tiny real video file from a bundled ultralytics sample
    image, so the video-file frame source is tested against a real file
    on disk rather than mocked."""
    import ultralytics

    assets_dir = os.path.join(os.path.dirname(ultralytics.__file__), "assets")
    src_image = os.path.join(assets_dir, "bus.jpg")
    img = cv2.imread(src_image)
    h, w = img.shape[:2]

    video_path = str(tmp_path / "test_video.mp4")
    writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), 5, (w, h))
    for _ in range(8):
        writer.write(img)
    writer.release()

    return video_path


def test_demo_mode_returns_a_file_path():
    settings.YOLO_FRAME_SOURCE = "demo"
    try:
        frame = _get_frame()
        assert isinstance(frame, str)
        assert os.path.exists(frame)
    finally:
        settings.YOLO_FRAME_SOURCE = "demo"


def test_video_file_mode_returns_real_frames(demo_video_path):
    settings.YOLO_FRAME_SOURCE = demo_video_path
    try:
        frame = _get_frame()
        assert hasattr(frame, "shape")  # a numpy array, not a path
        assert frame.shape[0] > 0 and frame.shape[1] > 0
    finally:
        settings.YOLO_FRAME_SOURCE = "demo"


def test_video_file_loops_past_end_of_clip(demo_video_path):
    """The test video has 8 frames — reading more than that should loop
    rather than raise or hang."""
    settings.YOLO_FRAME_SOURCE = demo_video_path
    try:
        for _ in range(12):
            frame = _get_frame()
            assert frame.shape[0] > 0
    finally:
        settings.YOLO_FRAME_SOURCE = "demo"


def test_missing_frame_source_raises_detector_unavailable():
    settings.YOLO_FRAME_SOURCE = "/nonexistent/path/video.mp4"
    try:
        with pytest.raises(DetectorUnavailable):
            _get_frame()
    finally:
        settings.YOLO_FRAME_SOURCE = "demo"
