import enum
from typing import Optional

class BlendType(enum.IntEnum):
    Unknown = -1
    TurnAngle = 0
    Distance = 1

class FocusCompatibility(enum.IntEnum):
    Unknown = -1
    Full = 0

