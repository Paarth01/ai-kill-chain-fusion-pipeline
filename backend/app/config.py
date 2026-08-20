import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Fusion tuning
    FUSION_DISTANCE_THRESHOLD_KM: float = float(os.getenv("FUSION_DISTANCE_THRESHOLD_KM", 1.5))
    FUSION_TIME_WINDOW_SECONDS: int = int(os.getenv("FUSION_TIME_WINDOW_SECONDS", 30))
    TRACK_STALE_AFTER_SECONDS: int = int(os.getenv("TRACK_STALE_AFTER_SECONDS", 120))

    # Feed simulation rates
    VEHICLE_IR_INTERVAL: float = float(os.getenv("VEHICLE_IR_INTERVAL", 2))
    UAV_UAS_INTERVAL: float = float(os.getenv("UAV_UAS_INTERVAL", 3))
    ELINT_INTERVAL: float = float(os.getenv("ELINT_INTERVAL", 4))
    LEGACY_C2_INTERVAL: float = float(os.getenv("LEGACY_C2_INTERVAL", 5))

    # Real YOLOv8n detection mode (requires requirements-detection.txt)
    ENABLE_REAL_DETECTION: bool = os.getenv("ENABLE_REAL_DETECTION", "false").lower() == "true"

    # Path to model weights — defaults to stock yolov8n.pt (auto-downloaded
    # by ultralytics on first use). Point this at your own trained weights
    # (e.g. from the Purplle Tech Challenge project) to use them instead —
    # no code change needed.
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")

    # Frame source for real-detection mode:
    #   "demo"          -> bundled ultralytics sample images (default)
    #   "webcam"        -> local webcam via OpenCV (device index 0)
    #   <path to file>  -> a video file or image, read via OpenCV
    YOLO_FRAME_SOURCE: str = os.getenv("YOLO_FRAME_SOURCE", "demo")

    # Distributed mode: when set, feeds/fusion communicate over a Redis list
    # instead of an in-process asyncio.Queue, so producers and the fusion
    # worker can run as separate processes/containers. Unset = in-memory.
    REDIS_URL: str | None = os.getenv("REDIS_URL") or None
    REDIS_QUEUE_KEY: str = os.getenv("REDIS_QUEUE_KEY", "sentinel:readings")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))

    # CORS: comma-separated list of allowed frontend origins. Defaults to
    # local dev (Vite's default port). Set to your deployed frontend's
    # origin (e.g. https://your-app.vercel.app) in production.
    ALLOWED_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]

    # API key required on mutating endpoints (ack/assess/EW toggle) via an
    # X-API-Key header. Left unset by default (auth disabled) so local
    # development and the test suite work out of the box — set this
    # before any real deployment. Deliberately NOT applied to /stream/tracks:
    # browsers' EventSource API cannot send custom headers, so an SSE
    # endpoint can't be protected this way without a different scheme
    # (e.g. a short-lived signed query param) — noted here rather than
    # silently left as a gap.
    API_KEY: str | None = os.getenv("API_KEY") or None

    # Stage-event history persistence. Defaults to a local SQLite file
    # (zero setup); set to a postgres:// URL to use Postgres instead — the
    # same async code path handles both (see persistence/db.py).
    DATABASE_URL: str | None = os.getenv("DATABASE_URL") or None


settings = Settings()
