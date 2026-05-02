from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ModuleError(Exception):
    error: str
    message: str
    status_code: int = 400
    hint: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message
