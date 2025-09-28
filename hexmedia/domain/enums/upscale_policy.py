from __future__ import annotations
from enum import StrEnum

class UpscalePolicy(StrEnum):
    never = "never"
    if_smaller_than = "if_smaller_than"
    always = "always"
