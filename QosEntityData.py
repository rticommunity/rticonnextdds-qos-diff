from __future__ import annotations
from dataclasses import dataclass
from QosEntities import QosEntitiesEnum
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class QosEntityData:
    library: str = ""
    profile: str = ""
    entity_name: Optional[str] = None
    topic_filter: Optional[str] = None
    entity_type: Optional[QosEntitiesEnum] = None

    def __eq__(self, other):
        if not isinstance(other, QosEntityData):
            return NotImplemented
        return (self.library == other.library and
                self.profile == other.profile and
                self.entity_name == other.entity_name and
                self.topic_filter == other.topic_filter)

    def __hash__(self):
        return hash((self.library, self.profile, self.entity_name, self.topic_filter))

    def __lt__(self, other: QosEntityData) -> bool:
        return ((self.library, self.profile, self.entity_name or "") <
                (other.library, other.profile, other.entity_name or ""))

    def __str__(self) -> str:
        return self.join()

    def join(self) -> str:
        parts = [self.library, self.profile]
        if self.has_topic_filter():
            parts.append(self.entity_name or self.topic_filter)
        return "::".join(parts)

    def split_entity_name(self) -> tuple[str, Optional[str]]:
        return (f"{self.library}::{self.profile}", self.entity_name)

    def is_default(self) -> bool:
        return (self.library == "" and self.profile == "" and
                self.entity_name is None and self.topic_filter is None)

    def has_topic_filter(self) -> bool:
        return self.topic_filter is not None

    def get_topic_filter(self) -> Optional[str]:
        return self.topic_filter

    @staticmethod
    def join_sets(set_a: set[QosEntityData], set_b: set[QosEntityData]) -> list[tuple[QosEntityData, QosEntityData]]:
        # Step 1: Index by (library, profile, entity, topic_filter)
        index1 = {(q.library, q.profile, q.entity_name, q.topic_filter): q for q in set_a}
        index2 = {(q.library, q.profile, q.entity_name, q.topic_filter): q for q in set_b}

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
            # Could also return profile_1.join()
            return profile_0.join()
        elif not profile_0.is_default() and not profile_1.is_default():
            # If they are not equal, but both defined, return profile_1
            return profile_1.join()
        elif profile_0 != QosEntityData():
            return profile_0.join()
        elif profile_1 != QosEntityData():
            return profile_1.join()
        logger.error(f"Both profiles are empty, cannot determine common profile name: {profiles}")
        raise ValueError("Cannot determine common profile name from two empty profiles")