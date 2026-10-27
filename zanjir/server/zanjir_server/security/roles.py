"""Rollar ierarxiyasi: ADMIN > LEAD > ENGINEER > VIEWER (prompt 7-bo'lim)."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    VIEWER = "VIEWER"
    ENGINEER = "ENGINEER"
    LEAD = "LEAD"
    ADMIN = "ADMIN"

    @property
    def level(self) -> int:
        return _LEVEL[self]

    def at_least(self, other: Role) -> bool:
        return self.level >= other.level


_LEVEL = {Role.VIEWER: 0, Role.ENGINEER: 1, Role.LEAD: 2, Role.ADMIN: 3}

# Kim qaysi rolga taklif yubora oladi: ADMIN — hammaga, LEAD — muhandis va kuzatuvchiga.
INVITABLE: dict[Role, frozenset[Role]] = {
    Role.ADMIN: frozenset(Role),
    Role.LEAD: frozenset({Role.ENGINEER, Role.VIEWER}),
    Role.ENGINEER: frozenset(),
    Role.VIEWER: frozenset(),
}

# Protokolni imzolay oladigan rollar (ADR-0010) va laboratoriya sozlamalari muharrirlari (ADR-0009).
SIGNERS = frozenset({Role.LEAD, Role.ENGINEER})
EDITORS = frozenset({Role.LEAD, Role.ADMIN})
