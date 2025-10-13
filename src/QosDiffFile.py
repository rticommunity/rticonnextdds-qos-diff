import logging
import os
from enum import IntEnum

from src.QosEntities import QosEntitiesEnum

logger = logging.getLogger(__name__)

class QosType(IntEnum):
    BASE = 0
    DIFF = 1

class QosDiffFile:
    def __init__(self, out_dir, type):
        self.type = type
        self.path = os.path.join(out_dir, 'base_qos.xml' if self.type == QosType.BASE else 'diff_qos.xml')
        self.version = ''

    def get_entity_path(self, entity_name: QosEntitiesEnum) -> str:
        return f'{entity_name.value}_base.xml' if self.type == QosType.BASE else f'{entity_name.value}_diff.xml'