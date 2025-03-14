import os
import subprocess
import sys
from utils import *

def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"Error: Command '{command}' failed with return code {result.returncode}")
        print(result.stdout.decode())
        print(result.stderr.decode())
        sys.exit(1)
    else:
        # print(result.stdout.decode())
        pass

def main():
    connext_install_root = os.path.dirname(os.getenv('NDDSHOME'))
    connext_installations = find_rti_connext_dds_dirs(connext_install_root)

    print('RTI Connext DDS Installations Found:')
    for installation in connext_installations:
        print(f"  {installation}")
    print()

    if not connext_installations:
        print("No RTI Connext DDS installations found.")
        sys.exit(1)

    print(f"Building for RTI Connext DDS installations:")

    for installation in connext_installations:
        build_dir = os.path.join(RTI_XML_UTILITY_PATH, 'build', installation)

        # Create the build directory if it doesn't exist
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)

        # Run CMake to configure the project
        cmake_command = f'cmake -DCONNEXTDDS_DIR={os.path.join(connext_install_root, installation)} \
            -DCONNEXTDDS_ARCH={os.getenv("CONNEXTDDS_ARCH")} {RTI_XML_UTILITY_PATH}'
        run_command(cmake_command, cwd=build_dir)

        # Run the build command
        build_command = 'cmake --build .'
        run_command(build_command, cwd=build_dir)

        print(f"  {installation} built successfully.")

if __name__ == "__main__":
    main()