"""SARM trained on failed recordings too (see ``sarm``, ``failures = "flat"``).

The paper trains on successful demonstrations only. Here the failed recordings are added:
their grip steps are labelled as in a success, and every press step is held at the start of
the press stage (tau = 0), so pressing without a click earns no progress.
"""

from __future__ import annotations

from reward_models import sarm

NAME = "sarm_failures"
METRIC = sarm.METRIC
DEFAULTS = {**sarm.DEFAULTS, "failures": "flat"}

train = sarm.make_train(DEFAULTS)
Model = sarm.make_model(DEFAULTS)
