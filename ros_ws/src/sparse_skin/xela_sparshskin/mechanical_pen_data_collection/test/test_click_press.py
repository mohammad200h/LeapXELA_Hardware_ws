"""Click press against a simulated thumb: joint springs (kP, current limit) pressing a pen
button with friction, which clicks."""

import numpy as np

from mechanical_pen_data_collection import click_press as cp

# Fingertip Jacobian (m/rad): anisotropic, as on the thumb, so an IK push along z makes a force
# well off z.
J = np.array([
    [0.050, 0.000, 0.030, 0.010],
    [0.000, 0.040, 0.030, 0.000],
    [0.010, 0.010, 0.030, 0.040],
])
KP = np.array([0.75, 1.0, 1.0, 1.0]) * 2.0  # torque per rad of goal error (motor 0 at 75 %)
K_PEN = 3000.0  # force units per m pressed into the button
K_T = 3000.0  # force units per m of tangential stretch before slipping
PEAK = 6.0  # recorded peak fingertip force
NOISE = 0.2
F_CLICK = 5.5  # the button clicks at this force ...
TRAVEL = 0.003  # ... and gives way this far
SURFACE = 0.002  # m from the region's start point to the button along the pen axis
EFFORT_AT_LIMIT = 650.0  # leap_state effort of a joint at its current limit
Z = np.array([0.0, 0.0, 1.0])


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def tilt(axis_deg, about=(0.0, 1.0, 0.0)):
    """Z turned by ``axis_deg`` degrees about ``about``."""
    a = np.radians(axis_deg)
    k = unit(about)
    return unit(Z * np.cos(a) + np.cross(k, Z) * np.sin(a))


class LinearKin:
    def point_and_jacobian(self, q):
        return J @ q, J

    def point(self, q_hand):
        return None if q_hand is None else J @ q_hand


class Thumb:
    """Quasi-static thumb: each joint a spring toward its goal (torque capped), the fingertip
    against a button surface (normal ``n``) with stick / slip friction ``mu``."""

    def __init__(self, q, n=Z, mu=0.6, tau_max=1.0, pen=True, clicks=True, mic=False):
        self.q = np.array(q, dtype=float)
        self.x0 = J @ self.q
        self.n = unit(n)
        self.mu, self.tau_max, self.pen, self.clicks, self.mic = mu, tau_max, pen, clicks, mic
        self.surface = SURFACE
        self.anchor = None  # where the fingertip sticks on the button
        self.clicked = False
        self.click_count = 0
        self.slid = 0.0  # m slid over the button in total
        self.f = np.zeros(3)
        self.torque = np.zeros(4)

    def contact_force(self, x):
        depth = float(np.dot(x - self.x0, self.n)) - self.surface
        if not self.pen or depth <= 0.0:
            self.anchor = None
            return np.zeros(3), depth
        if self.anchor is None:
            self.anchor = x.copy()
        stretch = x - self.anchor
        stretch -= np.dot(stretch, self.n) * self.n
        f_n = K_PEN * depth
        f_t = K_T * stretch
        limit = self.mu * f_n
        if np.linalg.norm(f_t) > limit:  # slip: the anchor follows
            excess = (np.linalg.norm(f_t) - limit) / K_T
            self.anchor += unit(stretch) * excess
            self.slid += excess
            f_t = unit(f_t) * limit
        return f_n * self.n + f_t, depth

    def settle(self, goal, iterations=150):
        for _ in range(iterations):
            torque = np.clip(KP * (goal - self.q), -self.tau_max, self.tau_max)
            f, _ = self.contact_force(J @ self.q)
            self.q += 0.08 * (torque - J.T @ f) / KP
        self.torque = np.clip(KP * (goal - self.q), -self.tau_max, self.tau_max)
        self.f, depth = self.contact_force(J @ self.q)
        f_n = float(np.dot(self.f, self.n))
        if self.clicks and not self.clicked and f_n >= F_CLICK:
            self.clicked = True
            self.surface += TRAVEL
            self.click_count += int(self.mic)
            self.settle(goal, iterations)

    @property
    def force(self):
        return NOISE + float(np.linalg.norm(self.f))

    @property
    def effort(self):
        return self.torque / self.tau_max * EFFORT_AT_LIMIT


def run(thumb, axis=Z, seconds=25.0, ik_press=False, **settings):
    """Plays a region 1-20 s; returns (press, thumb, local where the take resumed, mm slid
    between contact and the click (or the end of the press))."""
    geometry = cp.PressGeometry(axis=unit(axis), peak=PEAK, noise=NOISE, weights=np.ones(1),
                                loading=0.009)
    region = cp.PressRegion(start=1.0, end=20.0, geometry=geometry, kin=LinearKin(),
                            kp=KP / KP.max())
    press = cp.ClickPress([region], cp.ClickPressSettings(**settings))
    if ik_press:  # the old press: goal offsets along the IK direction J+ d
        def ik_u():
            press._u = unit(np.linalg.pinv(J) @ press._d)
            press._u_age = 0.0
        press._update_u = ik_u
    press.reset(0.0)
    q_rec = thumb.q.copy()
    dt, now, held, resumed = 1 / 30, 0.0, 0.0, None
    goal = q_rec
    slid_from = slid_to = None
    while now < seconds:
        now += dt
        local = now - held
        thumb.settle(goal)
        step = press.step(local, dt, now, q_rec, thumb.q.copy(), thumb.force,
                          thumb.click_count, thumb.effort)
        if press.state == cp.PRESS:
            if slid_from is None:
                slid_from = thumb.slid
            if not thumb.clicked:
                slid_to = thumb.slid
        if step is None:
            goal = q_rec
            if resumed is not None and press.state == cp.DONE:
                break
            continue
        goal = step.q
        if step.hold:
            held += dt
        if step.skip_to is not None:
            held -= step.skip_to - local
            resumed = step.skip_to
    slid = (slid_to - slid_from) * 1000 if slid_from is not None else 0.0
    return press, thumb, resumed, slid


def events(press):
    return [e["event"] for e in press.trace]


def reason(press, event):
    found = [e["why"] for e in press.trace if e["event"] == event]
    return found[0] if found else ""


def test_ik_push_force_is_off_axis_jacobian_transpose_is_not():
    # A goal offset along the IK direction makes a fingertip force along (J J^T)^-1 d.
    ik = np.linalg.solve(J @ J.T, Z)
    assert np.degrees(np.arccos(unit(ik) @ Z)) > np.degrees(np.arctan(0.3))
    # The J^T direction (over the joints' kP) makes it along d.
    u = J.T @ Z / (KP / KP.max())
    force = np.linalg.pinv(J.T) @ (KP * u)
    assert np.degrees(np.arccos(unit(force) @ Z)) < 1.0


def test_jacobian_transpose_press_slides_less_than_ik_press():
    _, ik_thumb, _, ik_slid = run(Thumb(np.zeros(4), mu=0.3, mic=True), ik_press=True)
    press, thumb, _, slid = run(Thumb(np.zeros(4), mu=0.3, mic=True))
    assert ik_slid > 1.0  # mm: the old press slides on the cap
    assert slid < 0.2
    assert thumb.clicked and "click" in events(press)


def test_press_clicks_and_resumes_the_take():
    press, thumb, resumed, slid = run(Thumb(np.zeros(4), mic=True))
    assert thumb.clicked and reason(press, "click") == "click detector"
    assert press.slips == 0 and slid < 0.2
    assert resumed == 20.0 and press.state == cp.DONE


def test_click_from_force_drop_and_give_way_without_detector():
    press, thumb, _, _ = run(Thumb(np.zeros(4), mic=False))
    assert thumb.clicked
    assert "gave way" in reason(press, "click")


def test_require_click_detector_ignores_drops():
    press, thumb, _, _ = run(Thumb(np.zeros(4), mic=False), require_click_detector=True)
    assert thumb.clicked  # the button clicked, but nothing heard it
    assert "click" not in events(press)


def test_current_limit_holds_then_gives_up():
    press, thumb, resumed, _ = run(Thumb(np.zeros(4), tau_max=0.08, mic=True))
    assert not thumb.clicked
    assert "saturated" in events(press)
    assert "current limit" in reason(press, "abort")
    assert resumed == 20.0


def test_no_pen_aborts_within_max_travel():
    press, _, resumed, _ = run(Thumb(np.zeros(4), pen=False))
    assert "no contact" in reason(press, "abort")
    assert resumed == 20.0


class Scripted:
    """Drives ``ClickPress`` straight into its press with scripted measurements."""

    def __init__(self, **settings):
        geometry = cp.PressGeometry(axis=Z, peak=PEAK, noise=NOISE, weights=np.ones(1),
                                    loading=0.009)
        self.region = cp.PressRegion(start=0.0, end=10.0, geometry=geometry, kin=LinearKin())
        self.press = cp.ClickPress([self.region], cp.ClickPressSettings(**settings))
        self.press.reset(0.0)
        self.now = 0.0
        self.q = np.zeros(4)

    def step(self, force, point_offset=np.zeros(3), spot=None):
        """One step with the measured fingertip at ``point_offset`` from the start."""
        self.now += 1 / 30
        q_meas = np.linalg.pinv(J) @ point_offset
        return self.press.step(self.now, 1 / 30, self.now, self.q, q_meas, force, 0,
                               np.zeros(4), spot)

    def into_press(self, spot=None):
        self.step(3.0, spot=spot)  # at once above the contact level
        assert self.press.state == cp.PRESS


def test_slip_across_backs_off_and_reaims():
    sim = Scripted()
    sim.into_press()
    for _ in range(30):  # the press builds an offset
        sim.step(3.0)
    x = np.array([1.0, 0.0, 0.0])
    for k in range(1, 30):  # then the fingertip slides along +x, the force flat
        before = sim.press.press_offset
        sim.step(3.0, x * 0.0002 * k)
        if sim.press.slips:
            break
    assert sim.press.slips == 1 and "across d" in reason(sim.press, "slip")
    assert sim.press.press_offset < 0.75 * before  # 0.6 x, plus this step's push
    assert sim.press._d[0] < 0.0  # turned against the slip
    assert abs(np.degrees(np.arccos(sim.press._d @ Z)) - 10.0) < 0.5


def test_contact_spot_moving_on_the_pad_is_a_slip():
    sim = Scripted()
    sim.into_press(spot=np.zeros(3))
    for k in range(1, 30):
        sim.step(3.0, spot=np.array([0.0, 0.0002 * k, 0.0]))
        if sim.press.slips:
            break
    assert sim.press.slips == 1 and "on the pad" in reason(sim.press, "slip")


def test_keeps_sliding_gives_up():
    sim = Scripted()
    sim.into_press()
    x = np.array([1.0, 0.0, 0.0])
    offset = np.zeros(3)
    for _ in range(200):
        offset = offset + x * 0.0005
        sim.step(3.0, offset)
        if sim.press.state != cp.PRESS:
            break
    assert "keeps sliding" in reason(sim.press, "abort")
    assert sim.press.slips == 4


def test_a_force_drop_while_sliding_is_not_a_click():
    sim = Scripted()
    sim.into_press()
    for _ in range(20):
        sim.step(5.5)
    x = np.array([0.0, 1.0, 0.0])
    for k in range(1, 15):  # slides and the force drops, as off the edge of the cap
        sim.step(5.5 - 0.3 * k, x * 0.0004 * k + Z * 0.0003 * k)
    assert "click" not in events(sim.press)
    assert "slip" in events(sim.press)


def test_press_geometry_axis_is_the_loading_motion():
    d = unit([-0.978, 0.104, -0.183])
    offsets = np.array([[0.0, 0.0, 0.0], [0.005, 0.0, 0.0], [0.0, 0.005, 0.0]])
    t = np.linspace(0.0, 4.0, 200)
    depth = np.interp(t, [0, 1, 3, 4], [0, 0, 0.009, 0.009])
    force = np.interp(t, [0, 1.2, 3, 4], [0.2, 0.2, 7.4, 6.0])
    share = np.array([0.6, 0.3, 0.1])

    def positions_at(at):
        return offsets + float(np.interp(at, t, depth)) * d

    g = cp.press_geometry(0.5, 3.5, t, force[:, None] * share[None], positions_at)
    assert np.allclose(g.axis, d, atol=1e-3)
    assert abs(g.peak - 7.4) < 0.05
    assert np.allclose(g.weights, share)
    assert 0.006 < g.loading < 0.0091


def test_press_geometry_needs_loading_motion():
    t = np.linspace(0.0, 4.0, 200)
    force = np.interp(t, [0, 1, 3, 4], [0.2, 0.2, 7.0, 6.0])
    g = cp.press_geometry(
        0.5, 3.5, t, force[:, None] * np.ones((1, 3)) / 3, lambda at: np.zeros((3, 3))
    )
    assert g is None
