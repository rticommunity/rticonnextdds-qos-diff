##############################################################################################
# (c) 2024-2025 Copyright, Real-Time Innovations, Inc. (RTI) All rights reserved.
#
# RTI grants Licensee a license to use, modify, compile, and create derivative works of the
# software solely for use with RTI Connext DDS. Licensee may redistribute copies of the
# software, provided that all such copies are subject to this license. The software is
# provided "as is", with no warranty of any type, including any warranty for fitness for any
# purpose. RTI is under no obligation to maintain or support the software. RTI shall not be
# liable for any incidental or consequential damages arising out of the use or inability to
# use the software.
#
##############################################################################################

import logging
from enum import IntEnum
from pathlib import Path

from src.QosEntities import QosEntitiesEnum

logger = logging.getLogger(__name__)



# class QosDiffFile:
#     def __init__(self, out_dir: Path, type):
#         self.type = type
#         self.path = out_dir / ('base_qos.xml' if self.type == QosType.BASE else 'diff_qos.xml')
#         self.version = ''

#     def get_entity_path(self, entity_name: QosEntitiesEnum) -> str:
#         return f'{entity_name.value}_base.xml' if self.type == QosType.BASE else f'{entity_name.value}_diff.xml'