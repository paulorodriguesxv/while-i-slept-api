"""In-memory repositories for local development and tests."""

from __future__ import annotations

from copy import deepcopy

from while_i_slept_api.domain.models import (
    BriefingRecord,
    DeviceRegistration,
    EntitlementState,
    Provider,
    UserProfile,
)
from while_i_slept_api.repositories.base import BriefingRepository, DeviceRepository, UserRepository


class InMemoryUserRepository(UserRepository):
    """Stores user profiles in memory."""

    def __init__(self) -> None:
        self._users: dict[str, UserProfile] = {}
        self._provider_index: dict[tuple[Provider, str], str] = {}

    def get_by_id(self, user_id: str) -> UserProfile | None:
        user = self._users.get(user_id)
        return deepcopy(user) if user else None

    def get_by_provider_identity(self, provider: Provider, provider_user_id: str) -> UserProfile | None:
        user_id = self._provider_index.get((provider, provider_user_id))
        if not user_id:
            return None
        return self.get_by_id(user_id)

    def save(self, user: UserProfile) -> UserProfile:
        self._users[user.user_id] = deepcopy(user)
        self._provider_index[(user.provider, user.provider_user_id)] = user.user_id
        return deepcopy(user)

    def update_entitlements(self, user_id: str, entitlements: EntitlementState) -> UserProfile | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        user.entitlements = deepcopy(entitlements)
        self._users[user_id] = deepcopy(user)
        return deepcopy(user)


class InMemoryDeviceRepository(DeviceRepository):
    """Stores devices in memory."""

    def __init__(self) -> None:
        self._devices: dict[tuple[str, str], DeviceRegistration] = {}

    def upsert(self, device: DeviceRegistration) -> DeviceRegistration:
        self._devices[(device.user_id, device.device_id)] = deepcopy(device)
        return deepcopy(device)


class InMemoryBriefingRepository(BriefingRepository):
    """Stores briefings in memory."""

    def __init__(self) -> None:
        self._briefings: dict[tuple[str, str], BriefingRecord] = {}

    def get_for_user_date(self, user_id: str, date: str) -> BriefingRecord | None:
        briefing = self._briefings.get((user_id, date))
        return deepcopy(briefing) if briefing else None

    def save(self, briefing: BriefingRecord) -> BriefingRecord:
        self._briefings[(briefing.user_id, briefing.date)] = deepcopy(briefing)
        return deepcopy(briefing)
