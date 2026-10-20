"""
Press/release pairing of click events.

A push-button pen makes two sounds: one on press, one on release. Keyboard typing
also makes sharp clicks, but in bursts. A pen click is therefore accepted only as
two events whose gap is in ``[min_gap, max_gap]``, with no other event in the
``quiet`` seconds before the press, between the two, or in the ``quiet`` seconds
after the release.

Times are in seconds on the audio clock (sample count / sample rate). ``latency``
is how long after it happened an event may still be added; decisions that depend
on the absence of an event wait that much longer. Plain Python so it can be tested
without ROS.
"""

from __future__ import annotations

import collections
import math


class PressReleasePairer:
    def __init__(
        self, min_gap: float, max_gap: float, quiet: float, latency: float = 0.0
    ) -> None:
        if not 0.0 <= min_gap <= max_gap:
            raise ValueError(f"Need 0 <= min_gap <= max_gap, got {min_gap}, {max_gap}")
        self.min_gap = min_gap
        self.max_gap = max_gap
        self.quiet = quiet
        self.latency = latency
        self._events: collections.deque[float] = collections.deque()
        self._prev = -math.inf  # last event no longer pending

    def add_event(self, t: float) -> None:
        """Record an event at ``t``; events must be added in time order."""
        self._events.append(t)

    def update(self, now: float) -> list[tuple[float, float]]:
        """``(press, release)`` times of the clicks that became certain by ``now``."""
        clicks = []
        while self._events:
            press = self._events[0]
            if press - self._prev < self.quiet:
                self._drop()  # too close to what came before: part of a burst
                continue
            if len(self._events) < 2:
                if now - press > self.max_gap + self.latency:
                    self._drop()  # no release in time
                break
            release = self._events[1]
            if not self.min_gap <= release - press <= self.max_gap:
                self._drop()
                continue
            if len(self._events) > 2:
                if self._events[2] - release < self.quiet:
                    self._drop()
                    continue
            elif now - release < self.quiet + self.latency:
                break  # wait to see whether anything follows the release
            clicks.append((press, release))
            self._events.popleft()
            self._events.popleft()
            self._prev = release
        return clicks

    def _drop(self) -> None:
        self._prev = self._events.popleft()
