from push_button_pen_click_detection.click_pairing import PressReleasePairer


def _run(events, end, quiet=0.15):
    pairer = PressReleasePairer(min_gap=0.05, max_gap=0.5, quiet=quiet)
    clicks = []
    for t in events:
        clicks += pairer.update(t)
        pairer.add_event(t)
    return clicks + pairer.update(end)


def test_isolated_pair_is_a_click():
    assert _run([1.0, 1.23], end=2.0) == [(1.0, 1.23)]


def test_pair_waits_for_quiet_after_release():
    pairer = PressReleasePairer(min_gap=0.05, max_gap=0.5, quiet=0.15)
    pairer.add_event(1.0)
    pairer.add_event(1.23)
    assert pairer.update(1.3) == []
    assert pairer.update(1.4) == [(1.0, 1.23)]


def test_single_event_is_not_a_click():
    assert _run([1.0], end=3.0) == []


def test_gap_out_of_range():
    assert _run([1.0, 1.8], end=3.0) == []
    assert _run([1.0, 1.03], end=3.0) == []


def test_typing_burst_is_rejected():
    typing = [1.0 + 0.11 * i for i in range(12)]
    assert _run(typing, end=4.0) == []


def test_click_after_typing():
    typing = [1.0 + 0.11 * i for i in range(6)]
    assert _run(typing + [3.0, 3.2], end=4.0) == [(3.0, 3.2)]


def test_key_right_after_release_cancels():
    assert _run([1.0, 1.2, 1.3], end=3.0, quiet=0.25) == []
    # With a shorter quiet_s the last two are an isolated pair
    assert _run([1.0, 1.2, 1.3], end=3.0, quiet=0.15) == [(1.2, 1.3)]


def test_consecutive_clicks():
    assert _run([1.0, 1.2, 2.0, 2.25], end=3.0) == [(1.0, 1.2), (2.0, 2.25)]


def test_waits_for_late_events():
    # Events are added 0.1 s after they happen. The key at 1.4 is within quiet of the
    # release at 1.2 but only known at 1.5, after quiet has passed: it must still cancel.
    def run(latency):
        pairer = PressReleasePairer(min_gap=0.05, max_gap=0.5, quiet=0.25, latency=latency)
        clicks = []
        for t in (1.0, 1.2, 1.4):
            clicks += pairer.update(t + 0.1)
            pairer.add_event(t)
        return clicks + pairer.update(3.0)

    assert run(latency=0.0) == [(1.0, 1.2)]
    assert run(latency=0.1) == []
