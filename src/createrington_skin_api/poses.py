from __future__ import annotations

import random
from typing import cast

from ._poses import KNOWN_POSES, KnownPose


def random_pose() -> KnownPose:
    """Return a uniformly random pose name from ``KNOWN_POSES``."""
    return cast(KnownPose, random.choice(KNOWN_POSES))
