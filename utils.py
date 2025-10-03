import logging
import os
import re
import subprocess
import xml.etree.ElementTree as ET

from QosEntityData import QosEntityData
from QosEntities import QosEntitiesEnum
from QosDiffFile import QosDiffFile, QosType

logger = logging.getLogger(__name__)

RTI_XML_UTILITY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    'rticonnextdds-xml-output-utility/')

class NextProfile(Exception):
    pass

class BreakLoop(Exception):
    def __init__(self, value):
        self.error_count = value

def find_rti_connext_dds_dirs(search_path):
    pattern = re.compile(r'rti_connext_dds-\d+\.\d+\.\d+')
    matching_dirs = set()  # Use a set to ensure unique values

    for root, dirs, _ in os.walk(search_path, topdown=True):
        for dir_name in dirs:
            if pattern.search(dir_name):
                matching_dirs.add(dir_name)
        # Clear the dirs list to prevent os.walk from going into subdirectories
        dirs.clear()

    return matching_dirs

def find_qos_profiles(xml_file: QosDiffFile):
    tree = ET.parse(xml_file.path)
    root = tree.getroot()

    qos_profiles = set()

    # Search for all profiles
    for qos_library_element in root.findall('.//qos_library'):
        if (library_name := qos_library_element.get('name')):
            for qos_profile_element in qos_library_element.findall('.//qos_profile'):
                if (profile_name := qos_profile_element.get('name')):
                    profile = QosEntityData(library_name, profile_name)
                    qos_profiles.add(profile)
                    logger.debug(f"{xml_file.type.name} profile added: {profile}")
                    for entity_type in [QosEntitiesEnum.DATAWRITER, QosEntitiesEnum.DATAREADER, QosEntitiesEnum.TOPIC]:
                        qos_profiles.update(find_named_entities(profile, qos_profile_element, entity_type, xml_file.type))

    return qos_profiles

def find_named_entities(qos_profile: QosEntityData, node: ET.Element, entity_type: QosEntitiesEnum, file_type: QosType) -> list[QosEntityData]:
    entities = set()
    # When Connext reads a Qos file, if multiple profiles have the same topic filter, it only uses the first one.
    topic_filters_set = set()
    first_general_profile_found = False

    for elem in node.findall(f'.//{entity_type.value}'):
        topic_filter = elem.get("topic_filter")
        if topic_filter:
            if topic_filter in topic_filters_set:
                profile_name = qos_profile.join()
                error_str = f"Duplicate topic_filter '{topic_filter}' found in {file_type.name} profile '{qos_profile.join()}'. Only the first occurrence will be used."
                entity_name = elem.get('name', None)
                if entity_name:
                    error_str += f" Reference: '{profile_name}::{entity_name}'."
                logger.warning(error_str)
                continue
            entities.add(
                QosEntityData(
                    library=qos_profile.library,
                    profile=qos_profile.profile,
                    entity_name=elem.get('name', None),
                    topic_filter=topic_filter,
                    entity_type=entity_type
                )
            )
            topic_filters_set.add(topic_filter)
            logger.debug(f"{file_type.name} profile added: {qos_profile}")
        elif first_general_profile_found:
            profile_name = qos_profile.join()
            error_str = f"Multiple {entity_type.value} entities found in {file_type.name} profile '{profile_name}'. Only the first occurrence will be used."
            entity_name = elem.get('name', None)
            if entity_name:
                error_str += f" Reference: '{profile_name}::{entity_name}'."

            logger.warning(error_str)
            continue
        else:
            # This profile will be handled by the general expansion of LIBRARY::PROFILE.  Don't need to add it here.
            first_general_profile_found = True

    return list(entities)

def expand_qos_profile(qos_file: QosDiffFile, diff_path: str, qos_profile: QosEntityData, entity_type: QosEntitiesEnum):
    qos_profile_str, _ = qos_profile.split_entity_name()
    topic_filter = qos_profile.get_topic_filter()
    outfile = os.path.join(diff_path, qos_file.get_entity_path(entity_type))
    args = [
        os.path.join(RTI_XML_UTILITY_PATH, 'build', qos_file.version, 'rtixmloutpututility'),
        '-qosFile', qos_file.path,
        '-outputFile', outfile,
        '-qosProfile', qos_profile_str,
        '-qosTag', entity_type.value
    ]
    if topic_filter:
        args += ['-topicName', topic_filter]

    result = subprocess.run(args, capture_output=True, text=True)
    if result.stdout:
        logger.debug(result.stdout)
    if result.stderr:
        logger.error(result.stderr)

    if not os.path.exists(outfile):
        raise FileNotFoundError