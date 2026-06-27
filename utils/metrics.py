import time
from dataclasses import dataclass, field


@dataclass
class _TimerStats:
    count: int = 0
    total_seconds: float = 0.0
    min_seconds: float | None = None
    max_seconds: float | None = None

    def add(self, seconds: float) -> None:
        self.count += 1
        self.total_seconds += float(seconds)
        if self.min_seconds is None or seconds < self.min_seconds:
            self.min_seconds = float(seconds)
        if self.max_seconds is None or seconds > self.max_seconds:
            self.max_seconds = float(seconds)

    @property
    def avg_seconds(self) -> float | None:
        if self.count <= 0:
            return None
        return self.total_seconds / self.count


@dataclass
class BotMetrics:
    started_at: float = field(default_factory=time.time)

    # Moderation counters
    staged_users: int = 0
    bans: int = 0
    softbans: int = 0
    timeouts_set: int = 0
    timeouts_cleared: int = 0
    verifications_passed: int = 0

    # OCR stats
    ocr_calls: int = 0
    ocr_timer: _TimerStats = field(default_factory=_TimerStats)

    def uptime_seconds(self) -> float:
        return max(0.0, time.time() - self.started_at)

    def record_ocr(self, seconds: float) -> None:
        self.ocr_calls += 1
        self.ocr_timer.add(seconds)


_METRICS = BotMetrics()


def get_metrics() -> BotMetrics:
    return _METRICS

