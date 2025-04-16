import os
import re
import xml.etree.ElementTree as ET
import subprocess

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
    for qos_library in root.findall('.//qos_library'):
        library_name = qos_library.get('name')
        if library_name:
            for qos_profile in qos_library.findall('.//qos_profile'):
                profile_name = qos_profile.get('name')
                if profile_name:
                    qos_profiles.add((f"{library_name}::{profile_name}", f"{library_name}::{profile_name}"))
    return qos_profiles

def expand_qos_profile(qos_file, diff_path, qos_profile, entity, log_file):
    outfile = os.path.join(diff_path, qos_file.get_entity_path(entity))
    subprocess.run([
        os.path.join(RTI_XML_UTILITY_PATH, 'build', qos_file.version, 'rtixmloutpututility'),
        '-qosFile', qos_file.path,
        '-outputFile', outfile,
        '-qosProfile', qos_profile[qos_file.type.value],
        '-qosTag', entity
    ], stdout=log_file, stderr=log_file)

    if not os.path.exists(outfile):
        raise FileNotFoundError