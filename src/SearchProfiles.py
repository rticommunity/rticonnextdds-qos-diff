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
import os
import re
import sys
import xml.etree.ElementTree as ET

from pathlib import Path

from src.QosEntityData import QosEntityData
from src.QosDiffConstants import QosEntitiesEnum, QosType
from src.PrintColor import print_colored

logger = logging.getLogger(__name__)

def find_rti_connext_dds_dirs(search_path: Path):
    pattern = re.compile(r'rti_connext_dds-\d+\.\d+\.\d+')
    matching_dirs = set()  # Use a set to ensure unique values

    for root, dirs, _ in os.walk(search_path, topdown=True):
        for dir_name in dirs:
            if pattern.search(dir_name):
                matching_dirs.add(dir_name)
        # Clear the dirs list to prevent os.walk from going into subdirectories
        dirs.clear()

    return matching_dirs

def find_qos_profiles(qos_file: Path, qos_type: QosType) -> set[QosEntityData]:
    try:
        tree = ET.parse(qos_file)
    except ET.ParseError as e:
        logger.critical(f"Failed to parse XML file {qos_file}: {e}")
        sys.exit(1)
    root = tree.getroot()

    qos_profiles = set()

    # Search for all profiles
    for qos_library_element in root.findall('.//qos_library'):
        if (library_name := qos_library_element.get('name')):
            for qos_profile_element in qos_library_element.findall('.//qos_profile'):
                if (profile_name := qos_profile_element.get('name')):
                    profile = QosEntityData(library_name, profile_name)
                    qos_profiles.add(profile)
                    logger.debug(f"{qos_type.name} profile added: {profile}")
                    for entity_type in [QosEntitiesEnum.DATAWRITER, QosEntitiesEnum.DATAREADER, QosEntitiesEnum.TOPIC]:
                        qos_profiles.update(find_named_entities(profile, qos_profile_element, entity_type, qos_type))

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
                error_str = f"Topic_filter '{topic_filter}' found in {file_type.name} profile '{qos_profile.join()}'. Only the first occurrence will be used."
                entity_name = elem.get('name', None)
                if entity_name:
                    error_str += f" Reference: '{profile_name}::{entity_name}'."
                print_colored(logging.WARNING, "Duplicate Topic Filter", error_str)
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
            error_str = f"{entity_type.value.capitalize()} found in {file_type.name} profile '{profile_name}'. Only the first occurrence will be used."
            entity_name = elem.get('name', None)
            if entity_name:
                error_str += f" Reference: '{profile_name}::{entity_name}'."
            print_colored(logging.WARNING, "Multiple Entities", error_str)
            continue
        else:
            # This profile will be handled by the general expansion of LIBRARY::PROFILE.  Don't need to add it here.
            first_general_profile_found = True

    return list(entities)