import logging
import os
import re
import subprocess
import xml.etree.ElementTree as ET

from QosEntityData import QosEntityData
from QosEntities import QosEntitiesEnum
from QosDiffFile import QosDiffFile

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

def find_qos_profiles(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    qos_profiles = set()

    # Search for all profiles
    for qos_library_element in root.findall('.//qos_library'):
        if (library_name := qos_library_element.get('name')):
            for qos_profile_element in qos_library_element.findall('.//qos_profile'):
                if (profile_name := qos_profile_element.get('name')):
                    profile = QosEntityData(library_name, profile_name)
                    qos_profiles.add(profile)
                    qos_profiles.update(find_named_entities(profile, qos_profile_element, "datawriter_qos"))
                    qos_profiles.update(find_named_entities(profile, qos_profile_element, "datareader_qos"))
                    qos_profiles.update(find_named_entities(profile, qos_profile_element, "topic_qos"))

    return qos_profiles

def find_named_entities(qos_profile: QosEntityData, node: ET.Element, entity_type: str) -> list[QosEntityData]:
    entities = set()  # use a set to deduplicate automatically

    for elem in node.findall(f'.//{entity_type}'):
        if (topic_filter := elem.get("topic_filter")):  # walrus operator: assign and check at the same time
            entities.add(
                QosEntityData(
                    library=qos_profile.library,
                    profile=qos_profile.profile,
                    entity_name=elem.get('name', None),
                    topic_filter=topic_filter,
                    entity_type=QosEntitiesEnum(entity_type)
                )
            )

    return list(entities)

def expand_qos_profile(qos_file: QosDiffFile, diff_path: str, qos_profile: QosEntityData, entity_type: QosEntitiesEnum, delta: bool=False):
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
    if delta:
        args.append('-deltaProfile')

    result = subprocess.run(args, capture_output=True, text=True)
    if result.stdout:
        logger.debug(result.stdout)
    if result.stderr:
        logger.error(result.stderr)

    if not os.path.exists(outfile):
        raise FileNotFoundError