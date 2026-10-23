"""One elapsed-time driver for the turntable; playback remains owned by MainWindow."""
import math

from PySide6.QtCore import QObject, QElapsedTimer, QTimer, Qt, Signal


def angle_at_radius(metadata, ratio):
    """Solve the stylus/pivot circle against a groove radius, nearest the artwork pose."""
    px, py = metadata["arm_pivot"]
    cx, cy = metadata["record_center"]
    sx, sy = metadata["stylus"]
    ax, ay, vx, vy = px - cx, py - cy, sx - px, sy - py
    a, b = ax * vx + ay * vy, -ax * vy + ay * vx
    radius = metadata["record_radius"] * ratio
    cosine = (radius * radius - ax * ax - ay * ay - vx * vx - vy * vy) / (2 * math.hypot(a, b))
    if not -1 <= cosine <= 1:
        raise ValueError("Stylus cannot reach the configured groove radius")
    phase, offset = math.atan2(b, a), math.acos(cosine)
    candidates = [(math.degrees(phase + sign * offset) + 180) % 360 - 180 for sign in (-1, 1)]
    return min(candidates, key=abs)


class TurntableMotion(QObject):
    changed = Signal()
    transition_changed = Signal(bool)
    record_swapped = Signal()
    DEGREES_PER_SECOND = 200.0  # 33 1/3 RPM: exactly one revolution per 1.8 s.
    PHASES = (("lift", .22), ("withdraw", .42), ("remove", .32),
              ("empty", .10), ("insert", .32), ("return", .42), ("lower", .22))

    def __init__(self, metadata, parent=None):
        super().__init__(parent)
        self.rest_angle = angle_at_radius(metadata, 1.18)
        self.outer_angle = angle_at_radius(metadata, .88)
        self.inner_angle = angle_at_radius(metadata, .56)
        self.record_angle = 0.0
        self.arm_angle = self.rest_angle
        self.playing = False
        self.active = False
        self.entered = False
        self.progress = 0.0
        self.phase = "idle"
        self.arm_lift = 0.0
        self.record_opacity = 1.0
        self._phase_elapsed = 0.0
        self._phase_start = (self.arm_angle, self.arm_lift, self.record_opacity)
        self._arm_start = self._arm_target = self.arm_angle
        self._arm_elapsed = self._arm_duration = 0.0
        self._arm_paused = False
        self.clock = QElapsedTimer()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)

    @property
    def changing(self):
        return self.phase != "idle"

    @property
    def rotating(self):
        return self.playing and not self.changing

    def request_change(self):
        """One latest-request transition. The widget owns the pending track.

        Before the swap, only the destination changes. After a new record has
        appeared, withdraw/fade again from the current pose (never teleport).
        """
        was_changing = self.changing
        if self.phase in ("lift", "withdraw", "remove", "empty"):
            return
        self._arm_duration = self._arm_elapsed = 0.0
        self.entered = True
        self._begin_phase("remove" if self.phase == "insert" else "lift")
        if not was_changing:
            self.transition_changed.emit(True)
        self._sync_timer()
        self.changed.emit()

    def _begin_phase(self, phase):
        self.phase = phase
        self._phase_elapsed = 0.0
        self._phase_start = (self.arm_angle, self.arm_lift, self.record_opacity)
        if phase == "insert":
            # Swap at zero opacity, after the empty-platter hold. A late request
            # during that hold is therefore included without a stale frame.
            self.record_angle = 0.0
            self.record_swapped.emit()

    def _advance_change(self, seconds):
        while self.changing and seconds > 0:
            index = next(i for i, item in enumerate(self.PHASES) if item[0] == self.phase)
            duration = self.PHASES[index][1]
            delta = min(seconds, duration - self._phase_elapsed)
            self._phase_elapsed += delta
            seconds -= delta
            if duration - self._phase_elapsed < 1e-9:
                self._phase_elapsed = duration
            t = min(1.0, self._phase_elapsed / duration)
            eased = t * t * (3 - 2 * t)
            angle, lift, opacity = self._phase_start
            if self.phase == "lift":
                self.arm_lift = lift + (1 - lift) * eased
            elif self.phase == "withdraw":
                self.arm_angle = angle + (self.rest_angle - angle) * eased
            elif self.phase == "remove":
                self.record_opacity = opacity * (1 - eased)
            elif self.phase == "insert":
                self.record_opacity = eased
            elif self.phase == "return":
                self.arm_angle = angle + (self.target_angle() - angle) * eased
            elif self.phase == "lower":
                self.arm_lift = lift * (1 - eased)
            if self._phase_elapsed >= duration:
                if index + 1 < len(self.PHASES):
                    self._begin_phase(self.PHASES[index + 1][0])
                else:
                    self.phase = "idle"
                    self.arm_lift, self.record_opacity = 0.0, 1.0
                    self._arm_paused = not self.playing
                    self.transition_changed.emit(False)
        return seconds

    @property
    def arm_moving(self):
        return self._arm_elapsed < self._arm_duration

    def target_angle(self):
        return self.outer_angle + (self.inner_angle - self.outer_angle) * self.progress

    def _retarget(self, duration):
        self._arm_start, self._arm_target = self.arm_angle, self.target_angle()
        self._arm_elapsed = 0.0
        self._arm_duration = duration if abs(self._arm_target - self.arm_angle) > 1e-6 else 0.0
        self._arm_paused = False

    def set_progress(self, seconds, duration):
        progress = max(0.0, min(1.0, seconds / duration)) if duration and duration > 0 else 0.0
        if progress == self.progress:
            return
        self.progress = progress
        if self.changing:
            # Retarget a return already in flight from the actual current pose.
            if self.phase in ("return", "lower"):
                self._begin_phase("return")
        elif self.entered:
            self._retarget(.45)
        self._sync_timer()

    def set_playing(self, playing):
        playing = bool(playing)
        if playing == self.playing:
            return
        if self.timer.isActive():
            self._tick()  # Account for the fraction of a frame before the click.
        self.playing = playing
        if playing and not self.changing:
            if not self.entered:
                self.entered = True
                self._retarget(1.05)
            self._arm_paused = False
        else:
            self._arm_paused = True  # Pause never lifts/returns the arm.
        self._sync_timer()
        self.changed.emit()

    def set_active(self, active, dpr=1):
        self.active = bool(active)
        # A bounded refresh rate at high DPR; elapsed time still sets exact RPM.
        self.timer.setInterval(33 if dpr >= 2 else 16)
        self._sync_timer()

    def _sync_timer(self):
        needed = self.active and (self.changing or self.playing or (self.arm_moving and not self._arm_paused))
        if needed and not self.timer.isActive():
            self.clock.start()
            self.timer.start()
        elif not needed:
            self.timer.stop()
            self.clock.invalidate()

    def _tick(self):
        if not self.clock.isValid():
            return
        seconds = self.clock.nsecsElapsed() / 1_000_000_000
        self.clock.restart()
        self.advance(seconds)
        self._sync_timer()

    def advance(self, seconds):
        """Integrate a time delta; also used by deterministic render/tests."""
        if seconds <= 0:
            return
        changed = False
        if self.changing:
            seconds = self._advance_change(seconds)
            changed = True
        if self.rotating and seconds > 0:
            self.record_angle = (self.record_angle + self.DEGREES_PER_SECOND * seconds) % 360
            changed = True
        if self.arm_moving and not self._arm_paused:
            self._arm_elapsed = min(self._arm_duration, self._arm_elapsed + seconds)
            t = self._arm_elapsed / self._arm_duration
            eased = t * t * (3 - 2 * t)  # Smooth start/stop, no overshoot.
            self.arm_angle = self._arm_start + (self._arm_target - self._arm_start) * eased
            changed = True
        if changed:
            self.changed.emit()
        self._sync_timer()
