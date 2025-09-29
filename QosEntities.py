from enum import Enum

class QosEntitiesEnum(Enum):
    DOMAIN_PARTICIPANT = 'domain_participant_qos'
    PUBLISHER = 'publisher_qos'
    DATAWRITER = 'datawriter_qos'
    SUBSCRIBER = 'subscriber_qos'
    DATAREADER = 'datareader_qos'
    TOPIC = 'topic_qos'