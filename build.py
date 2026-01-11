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

import os
import subprocess
import sys
import argparse
import logging
import platform
import shutil

from pathlib import Path

from src.Utilities import RTI_XML_UTILITY_PATH, find_rti_connext_dds_dirs
from src.PrintColor import print_colored

# Configure logging to file
log_path = os.path.join(os.getcwd(), "./output/build.log")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# File handler - save detailed logs
os.makedirs(os.path.dirname(log_path), exist_ok=True)
file_handler = logging.FileHandler(log_path, mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
logger.addHandler(file_handler)

def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        logger.error(result.stdout.decode())
        logger.error(result.stderr.decode())
        raise subprocess.CalledProcessError(result.returncode, command)

def main():
    # Check for environment variables first
    env_connext_dir = os.environ.get('NDDSHOME')
    env_connext_arch = os.environ.get('CONNEXTDDS_ARCH')

    if env_connext_dir and env_connext_arch:
        connext_dir = env_connext_dir
        connext_arch = env_connext_arch
        print_colored(logging.INFO, "Info", f"Using environment variables: NDDSHOME={connext_dir}, CONNEXTDDS_ARCH={connext_arch}")
    else:
        # Argument parser fallback
        parser = argparse.ArgumentParser(description='Build RTI XML Output Utility.')
        parser.add_argument('--connext_dir', type=str, required=True, help='Specify the root path of the Connext DDS installation(s).')
        parser.add_argument('--connext_arch', type=str, required=True, help='Specify the Connext DDS architecture.')
        args = parser.parse_args()
        connext_dir = args.connext_dir
        connext_arch = args.connext_arch

    connext_dir = Path(connext_dir).resolve()
    connext_install_root = connext_dir.parent

    logger.debug(f"Connext Directory: {connext_dir}")
    logger.debug(f"Connext Architecture: {connext_arch}")

    connext_installations = set()
    connext_installations.update(find_rti_connext_dds_dirs(connext_install_root))
    # Filter out installations that are not at least version 6.1.0, convert to list and sort
    connext_installations = [x for x in connext_installations if x >= 'rti_connext_dds-6.1.0']
    connext_installations.sort()

    if not connext_installations:
        print_colored(logging.ERROR, "Error", "No RTI Connext DDS installations found.")
        sys.exit(1)

    print_colored(logging.INFO, "Connext Versions", "RTI Connext DDS Installations >= Connext 6.1.0 Found:")
    for installation in connext_installations:
        print(f"  {installation}")
        logger.debug(f"Found installation: {installation}")
    print()

    print(f"Building for RTI Connext DDS installations:")

    for installation in connext_installations:
        try:
            build_dir = os.path.join(RTI_XML_UTILITY_PATH, 'build', installation)

            # Create the build directory if it doesn't exist
            if not os.path.exists(build_dir):
                os.makedirs(build_dir)

            # Run CMake to configure the project
            cmake_command = f'cmake -DCONNEXTDDS_DIR="{os.path.join(connext_install_root, installation)}" \
                -DCONNEXTDDS_ARCH={connext_arch} {RTI_XML_UTILITY_PATH} \
                -DCMAKE_BUILD_TYPE=Release'

            if platform.system() == 'Windows':
                cmake_command += ' -A x64'

            run_command(cmake_command, cwd=build_dir)

            # Run the build command
            build_command = 'cmake --build . --config Release'
            run_command(build_command, cwd=build_dir)

            print_colored(logging.INFO, "Success", f"{installation} built successfully.")
            logger.info(f"{installation} built successfully.")
        except subprocess.CalledProcessError:
            shutil.rmtree(build_dir)
            print_colored(logging.ERROR, "Failed", f"Failed to build for {installation}.")
            logger.error(f"Failed to build for {installation}.")
            continue

if __name__ == "__main__":
    main()