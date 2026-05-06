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

import argparse
import logging
import os
import re
import subprocess
import sys

from pathlib import Path

from src.QosDiff import QosDiff
from src.QosDiffConstants import RTI_XML_UTILITY_PATH
from src.PrintColor import print_colored
from src.QosDiffConstants import QosType

logger = logging.getLogger(__name__)

def get_git_repo_root(file_path: Path) -> Path | None:
    try:
        repo_root = subprocess.check_output(
            ['git', '-C', str(file_path.parent), 'rev-parse', '--show-toplevel'],
            stderr=subprocess.STDOUT
        ).strip().decode('utf-8')
        return Path(repo_root)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.output.decode('utf-8')}")
        return None

def find_rti_connext_dds_dirs(search_path: Path) -> set:
    pattern = re.compile(r'rti_connext_dds-\d+\.\d+\.\d+')
    matching_dirs = set()  # Use a set to ensure unique values

    for root, dirs, _ in os.walk(search_path, topdown=True):
        for dir_name in dirs:
            if pattern.search(dir_name):
                matching_dirs.add(dir_name)
        # Clear the dirs list to prevent os.walk from going into subdirectories
        dirs.clear()

    return matching_dirs

def select_option(options: list[str]) -> str | None:
    # Print the options
    options_list = list(options)
    options_list.sort()
    options_list.append('Exit')
    for i, option in enumerate(options_list, start=1):
        print(f"{i}. {option}")

    # Prompt the user to select an option
    while True:
        try:
            choice = int(input("Please select an option by entering the corresponding number: "))
            if 1 <= choice < len(options_list):
                return options_list[choice - 1]
            elif choice == len(options_list):
                print_colored(logging.WARNING, "Exiting", "No diff will be performed.")
                sys.exit(0)
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(options_list)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_connext_versions(qos_diff: QosDiff, args: argparse.Namespace) -> None:
    connext_installations = find_rti_connext_dds_dirs(RTI_XML_UTILITY_PATH / 'build')

    # Use NDDSHOME as the default Connext version if the environment variable is set
    nddshome = os.environ.get("NDDSHOME")
    env_connext_dir = (
        os.path.basename(nddshome)
        if nddshome and os.path.basename(nddshome).startswith("rti_connext_dds-")
        else None)

    if not connext_installations:
        logger.error("Error: No RTI Connext DDS installations found.")
        sys.exit(1)

    if(args.versions):
        if len(connext_installations) < 2:
            logger.error("Error: Two RTI Connext DDS installations are required to diff versions.")
            sys.exit(1)
        print('Please select a Connext version for the baseline Qos file:')
        qos_diff.connext_version.set_version(select_option(connext_installations), QosType.BASE)
        print('\nPlease select a Connext version for the diff Qos file:')
        qos_diff.connext_version.set_version(select_option(connext_installations), QosType.DIFF)
    elif env_connext_dir in connext_installations and not args.ignore_nddshome:
        qos_diff.connext_version.set_version(env_connext_dir, QosType.BASE)
        qos_diff.connext_version.set_version(env_connext_dir, QosType.DIFF)
    else:
        if len(connext_installations) > 1:
            print('Please select a Connext version to use:')
            qos_diff.connext_version.set_version(select_option(connext_installations), QosType.BASE)
            qos_diff.connext_version.set_version(qos_diff.connext_version.get_version(QosType.BASE), QosType.DIFF)
        else:
            qos_diff.connext_version.set_version(next(iter(connext_installations)), QosType.BASE)
            qos_diff.connext_version.set_version(next(iter(connext_installations)), QosType.DIFF)

    print_str = f"Baseline: {qos_diff.connext_version.get_version(QosType.BASE)}"
    if not qos_diff.expand:
        print_str += f", Diff: {qos_diff.connext_version.get_version(QosType.DIFF)}"
    print_colored(logging.INFO, "Selected Connext Version(s)", print_str)
    logger.debug(f"Base version: {qos_diff.connext_version.get_version(QosType.BASE)}, Diff version: {qos_diff.connext_version.get_version(QosType.DIFF)}")
    if args.delta and not args.expand:
        print("Warning: --delta only applies when --expand is also specified.  Ignoring --delta.\n")