import os
import re
import subprocess
import xml.etree.ElementTree as ET

from QosEntityData import QosEntityData
from QosEntities import QosEntitiesEnum

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

    for root, dirs, files in os.walk(search_path, topdown=True):
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
        if (name := elem.get("name")):  # walrus operator: assign and check at the same time
            entities.add(
                QosEntityData(
                    library=qos_profile.library,
                    profile=qos_profile.profile,
                    entity=name,
                    entity_type=QosEntitiesEnum(entity_type)
                )
            )

    return list(entities)

def find_named_entities_in_profile(profile: QosEntityData) -> dict[str, list[str]]:
    # TODO: Handle None xml_element
    if profile.xml_element is None:
        return {
            "writers": [],
            "readers": [],
            "topics": []
        }

    entity_map = {
        "writers": ".//datawriter_qos",
        "readers": ".//datareader_qos",
        "topics": ".//topic_qos",
    }

    results = {key: [] for key in entity_map}

    for key, xpath in entity_map.items():
        for elem in profile.xml_element.findall(xpath):
            if (name := elem.get("name")):
                results[key].append(name)

    return results

def expand_qos_profile(qos_file, diff_path, qos_profile, entity, log_file, entity_name=None):
    outfile = os.path.join(diff_path, qos_file.get_entity_path(entity))
    args = [
        os.path.join(RTI_XML_UTILITY_PATH, 'build', qos_file.version, 'rtixmloutpututility'),
        '-qosFile', qos_file.path,
        '-outputFile', outfile,
        '-qosProfile', qos_profile,
        '-qosTag', entity
    ]
    if entity_name:
        args += ['-topicName', entity_name]

    subprocess.run(args, stdout=log_file, stderr=log_file)

    if not os.path.exists(outfile):
        raise FileNotFoundError