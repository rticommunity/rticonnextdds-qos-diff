from __future__ import annotations
import os
import re
import xml.etree.ElementTree as ET
import subprocess
from dataclasses import dataclass

RTI_XML_UTILITY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    'rticonnextdds-xml-output-utility/')

class NextProfile(Exception):
    pass

class BreakLoop(Exception):
    def __init__(self, value):
        self.error_count = value

@dataclass
class QosProfileData:
    library: str = ""
    profile: str = ""
    xml_element: ET.Element = None

    # Do not consider 'element' for equality and hashing
    def __eq__(self, other):
        if not isinstance(other, QosProfileData):
            return NotImplemented
        return self.library == other.library and self.profile == other.profile

    def __hash__(self):
        return hash((self.library, self.profile))

    def join(self):
        return f"{self.library}::{self.profile}"

    def join_with_entity_name(self, entity_name: str):
        return f"{self.library}::{self.profile}::{entity_name}"

    @staticmethod
    def join_sets(set_a: set[QosProfileData], set_b: set[QosProfileData]) -> list[tuple[QosProfileData, QosProfileData]]:
        # Step 1: Index by (library, profile)
        index1 = {(q.library, q.profile): q for q in set_a}
        index2 = {(q.library, q.profile): q for q in set_b}

        # Step 2: Collect union of keys
        all_keys = index1.keys() | index2.keys()

        # Step 3: Build list of tuples, filling with QosProfileData() where missing
        result = [
            (index1.get(k, QosProfileData()), index2.get(k, QosProfileData()))
            for k in all_keys
        ]

        return result

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
        library_name = qos_library_element.get('name')
        if library_name:
            for qos_profile_element in qos_library_element.findall('.//qos_profile'):
                profile_name = qos_profile_element.get('name')
                if profile_name:
                    qos_profiles.add(
                        QosProfileData(library_name, profile_name, qos_profile_element)
                    )
    return qos_profiles

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