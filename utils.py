import os
import re

RTI_XML_UTILITY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    'rticonnextdds-xml-output-utility/')

def find_rti_connext_dds_dirs(search_path):
    pattern = re.compile(r'rti_connext_dds-\d+\.\d+\.\d+')
    matching_dirs = []

    for root, dirs, files in os.walk(search_path, topdown=True):
        for dir_name in dirs:
            if pattern.search(dir_name):
                matching_dirs.append(dir_name)
        # Clear the dirs list to prevent os.walk from going into subdirectories
        dirs.clear()

    matching_dirs.sort()
    return matching_dirs