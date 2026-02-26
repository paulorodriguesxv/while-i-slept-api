"""Repository interfaces and common container types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from while_i_slept_api.domain.models import (
    BriefingRecord,
    DeviceRegistration,
    EntitlementState,
    Provider,
    UserProfile,
)


class UserRepository(Protocol):
    """Persistence operations for user profiles."""

    def get_by_id(self, user_id: str) -> UserProfile | None:
        ...

    def get_by_provider_identity(
        self,
        provider: Provider,
        provider_user_id: str,
    ) -> UserProfile | None:
        ...

    def save(self, user: UserProfile) -> UserProfile:
        ...

    def update_entitlements(self, user_id: str, entitlements: EntitlementState) -> UserProfile | None:
        ...


class DeviceRepository(Protocol):
    """Persistence operations for devices."""

    def upsert(self, device: DeviceRegistration) -> DeviceRegistration:
        ...

    def list_by_user(self, user_id: str) -> list[DeviceRegistration]:
        ...


class BriefingRepository(Protocol):
    """Persistence operations for precomputed briefings."""

    def get_for_user_date(self, user_id: str, date: str) -> BriefingRecord | None:
        ...

    def save(self, briefing: BriefingRecord) -> BriefingRecord:
        ...


@dataclass(slots=True)
class RepositoryBundle:
    """Container for concrete repositories used by services."""

    users: UserRepository
    devices: DeviceRepository
    briefings: BriefingRepository
