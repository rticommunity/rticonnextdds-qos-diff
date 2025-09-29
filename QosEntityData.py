from __future__ import annotations
from dataclasses import dataclass
from QosEntities import QosEntitiesEnum
from typing import Optional

@dataclass
class QosEntityData:
    library: str = ""
    profile: str = ""
    entity: Optional[str] = None
    entity_type: Optional[QosEntitiesEnum] = None

    def __eq__(self, other):
        if not isinstance(other, QosEntityData):
            return NotImplemented
        return (self.library == other.library and
                self.profile == other.profile and
                self.entity == other.entity)

    def __hash__(self):
        return hash((self.library, self.profile, self.entity))

    def __lt__(self, other: QosEntityData) -> bool:
        return ((self.library, self.profile, self.entity or "") <
                (other.library, other.profile, other.entity or ""))

    def join(self, complete: bool = False) -> str:
        parts = [self.library, self.profile]
        if complete and self.entity:
            parts.append(self.entity)
        return "::".join(parts)

    @staticmethod
    def join_sets(set_a: set[QosEntityData], set_b: set[QosEntityData]) -> list[tuple[QosEntityData, QosEntityData]]:
        # Step 1: Index by (library, profile)
        index1 = {(q.library, q.profile, q.entity): q for q in set_a}
        index2 = {(q.library, q.profile, q.entity): q for q in set_b}

        # Step 2: Collect union of keys
        all_keys = index1.keys() | index2.keys()

        # Step 3: Build list of tuples, filling with QosEntityData() where missing
        result = [
            (index1.get(k, QosEntityData()), index2.get(k, QosEntityData()))
            for k in all_keys
        ]

        return result

    @staticmethod
    def get_common_profile_name(profiles: tuple[QosEntityData, QosEntityData]) -> str:
        profile_0, profile_1 = profiles
        if profile_0 == profile_1:
            return profile_0.join()
        elif profile_0 != QosEntityData():
            return profile_0.join()
        elif profile_1 != QosEntityData():
            return profile_1.join()
        raise ValueError("Cannot determine common profile name from two empty profiles")