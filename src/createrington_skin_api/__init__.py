"""Official Python client for the Createrington Skin API."""

from __future__ import annotations

from ._core import DEFAULT_BASE_URL, AvatarOptions
from ._poses import KNOWN_POSES, KnownPose, Poses
from .async_client import AsyncSkinApiClient
from .client import SkinApiClient
from .errors import SkinApiError, SkinApiErrorCode
from .poses import random_pose

__version__ = "2.5.0"

__all__ = [
    "AsyncSkinApiClient",
    "SkinApiClient",
    "SkinApiError",
    "SkinApiErrorCode",
    "AvatarOptions",
    "KNOWN_POSES",
    "KnownPose",
    "Poses",
    "random_pose",
    "DEFAULT_BASE_URL",
    "__version__",
]
