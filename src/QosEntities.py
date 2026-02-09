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

from enum import Enum, IntEnum

class QosType(IntEnum):
    BASE = 0
    DIFF = 1

class QosEntitiesEnum(Enum):
    DOMAIN_PARTICIPANT_FACTORY = 'domain_participant_factory_qos'
    DOMAIN_PARTICIPANT = 'domain_participant_qos'
    PUBLISHER = 'publisher_qos'
    DATAWRITER = 'datawriter_qos'
    SUBSCRIBER = 'subscriber_qos'
    DATAREADER = 'datareader_qos'
    TOPIC = 'topic_qos'