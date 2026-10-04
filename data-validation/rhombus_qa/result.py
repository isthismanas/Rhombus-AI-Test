from __future__ import annotations

from dataclasses import asdict, dataclass, field

PASS, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIP"


@dataclass
class Check:
    id: str
    name: str
    status: str
    message: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def overall(checks: list[Check]) -> str:
    statuses = {c.status for c in checks}
    if FAIL in statuses:
        return FAIL
    if WARN in statuses:
        return WARN
    return PASS
