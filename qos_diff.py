import os
import subprocess
import sys
import argparse
import shutil
import subprocess
import xml.etree.ElementTree as ET
import difflib
from  utils import *

class NextProfile(Exception):
    pass

class BreakLoop(Exception):
    pass

def get_git_repo_root(file_path):
    try:
        repo_root = subprocess.check_output(
            ['git', '-C', os.path.dirname(file_path), 'rev-parse', '--show-toplevel'],
            stderr=subprocess.STDOUT
        ).strip().decode('utf-8')
        return repo_root
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.output.decode('utf-8')}")
        return None

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

def compare_qos_files(profile_dir, entity, qos_profile):
    error_count = 0

    try:
        with open(os.path.join(profile_dir, f'{entity}_base.xml'), 'r') as file1, open(os.path.join(profile_dir, f'{entity}_diff.xml'), 'r') as file2:
            file1_lines = file1.readlines()
            file2_lines = file2.readlines()

        # Perform diff and get the line count
        diff_lines = list(difflib.unified_diff(file1_lines, file2_lines, fromfile=f'{entity}_base.xml', tofile=f'{entity}_diff.xml', lineterm=''))  # Convert the iterator to a list
        diff_line_count = len(diff_lines)

        # Write the diff to the file
        with open(os.path.join(profile_dir, f'{entity}_result.txt'), 'w') as diff_file:
            diff_file.writelines(diff_lines)

        if entity == 'domain_participant_qos':
            # diff_line_count will be 11 if process_id is only difference
            if diff_line_count != 11:
                print(f"Qos Failure | Profile: {qos_profile[1]} | Entity: {entity}")
                error_count += 1
        else:
            # Any difference in the profile is considered a failure
            if diff_line_count != 0:
                print(f"Qos Failure | Profile: {qos_profile[1]} | Entity: {entity}")
                error_count += 1

    except FileNotFoundError:
        # Determine which file is missing
        diff_missing = False
        if os.path.exists(os.path.join(profile_dir, f'{entity}_base.xml')):
            diff_missing = True
        if qos_profile[0] == qos_profile[1]:
            print(f"Error: {qos_profile[0]} not found in the {'diff' if diff_missing else 'base'} Qos file.")
        elif diff_missing:
            print(f"Error: {qos_profile[1]} not found in the diff Qos file.")
        else:
            print(f"Error: {qos_profile[0]} not found in the base Qos file.")
        error_count += 1
        raise NextProfile

    return error_count

def expand_qos_profile(base_qos, out_file, qos_profile, entity, log_file, version):
    subprocess.run([
        os.path.join(RTI_XML_UTILITY_PATH, 'build', version, 'rtixmloutpututility'),
        '-qosFile', base_qos,
        '-outputFile', out_file,
        '-qosProfile', qos_profile,
        '-qosTag', entity
    ], stdout=log_file, stderr=log_file)

def select_option(options):
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
                print("\nExiting.  No diff will be performed.")
                sys.exit(0)
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(options_list)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def main():
    # Argument parser setup
    parser = argparse.ArgumentParser(description='Diff two DDS QoS files. Two separate files or the same file from a previous Git commit can be diffed.')
    parser.add_argument('--qos_file', type=str, required=True, help='Required argument. Specify the Qos file.')
    parser.add_argument('--diff_file', type=str, default='', help='Specify a Qos file to diff.')
    parser.add_argument('--commit', type=str, default='', help='Specify the Git commit hash of the base file.')
    parser.add_argument('--profile', type=str, default='', help='Specify the Qos profile in the format: Library::Profile. Otherwise all profiles will be diffed.')
    parser.add_argument('--new_profile', type=str, default='', help='If the profile has been renamed in the diff file, specify the new Qos Profile in the format: Library::Profile.')
    parser.add_argument('--out_dir', type=str, default=os.path.join(os.getcwd(), 'output'), help='Output directory. Default is ${CWD}/output.')
    parser.add_argument('--rm', action='store_true', help='Delete intermediary diff output.')
    parser.add_argument('--break_on_failure', action='store_true', help='Break on diff failure.')
    parser.add_argument('--versions', action='store_true', help='Diff against two different versions of Connext DDS.')
    args = parser.parse_args()

    # Delete previous output directory
    if os.path.exists(args.out_dir):
        shutil.rmtree(args.out_dir)
    os.makedirs(args.out_dir)

    # Open the log file for the duration of the application
    with open(os.path.join(args.out_dir, 'log.txt'), 'w') as log_file:
        # Write all command-line arguments to the log file
        log_file.write("Command-line arguments:\n")
        for arg, value in vars(args).items():
            log_file.write(f"{arg}: {value}\n")
        log_file.write("\n")

        # Define Qos Files
        base_qos = os.path.join(args.out_dir, 'base_qos.xml')
        diff_qos = os.path.join(args.out_dir, 'diff_qos.xml')

        # Check if the Qos file exists
        if not os.path.exists(args.qos_file):
            print(f"Error: {args.qos_file} does not exist.")
            sys.exit(1)

        if args.commit != '':
            repo_path = get_git_repo_root(args.qos_file)
            result = subprocess.run(
                ['git', '-C', repo_path, 'show', f'{args.commit}:{os.path.relpath(args.qos_file, repo_path)}'],
                stdout=open(base_qos, 'w'),
                stderr=log_file
            )
            if result.returncode != 0:
                print(f"Error: Failed to get the base QoS file from the Git commit. See README for details.")
                sys.exit(1)
            shutil.copy(args.qos_file, diff_qos)
        elif args.diff_file != '':
            shutil.copy(args.qos_file, base_qos)
            shutil.copy(args.diff_file, diff_qos)
        else:
            print("Error: Must specify either --commit or --diff_file.")
            sys.exit(1)

        # Define the Profiles
        qos_profiles = set()

        if args.profile == '':
            qos_profiles.update(find_qos_profiles(base_qos))
            qos_profiles.update(find_qos_profiles(diff_qos))
        elif args.new_profile != '':
            qos_profiles.add((args.profile, args.new_profile))
        else:
            qos_profiles.add((args.profile, args.profile))

        entities = ['domain_participant_qos', 'publisher_qos', 'datawriter_qos', 'subscriber_qos', 'datareader_qos', 'topic_qos']

        # Formatting
        print()

        # USER_QOS_PROFILES.xml can't be in the working directory when diff is called.  Move up a directory.
        if args.qos_file == 'USER_QOS_PROFILES.xml' or args.diff_file == 'USER_QOS_PROFILES.xml':
            os.chdir('..')

        connext_installations = find_rti_connext_dds_dirs(os.path.join(RTI_XML_UTILITY_PATH, 'build'))
        if not connext_installations:
            print("Error: No RTI Connext DDS installations found.")
            sys.exit(1)
        if(args.versions):
            if len(connext_installations) < 2:
                print("Error: Two RTI Connext DDS installations are required to diff versions.")
                sys.exit(1)
            print('Please select a Connext version for the baseline Qos file.')
            base_version = select_option(connext_installations)
            print('\nPlease select a Connext version for the diff Qos file.')
            diff_version = select_option(connext_installations)
        else:
            print('Please select a Connext version to use.')
            base_version = select_option(connext_installations)
            diff_version = base_version
        print()

        error_count = 0
        try:
            for qos_profile in qos_profiles:
                try:
                    print(f"Diffing Qos Profile: {qos_profile[0]}")
                    profile_dir = os.path.join(args.out_dir, qos_profile[1])
                    os.makedirs(profile_dir)
                    for entity in entities:
                        entity_qos_out_path = os.path.join(profile_dir, f'{entity}_base.xml')
                        entity_diff_out_path = os.path.join(profile_dir, f'{entity}_diff.xml')
                        expand_qos_profile(base_qos, entity_qos_out_path, qos_profile[0], entity, log_file, base_version)
                        expand_qos_profile(diff_qos, entity_diff_out_path, qos_profile[1], entity, log_file, diff_version)

                        error_count += compare_qos_files(profile_dir, entity, qos_profile)

                        if args.rm:
                            os.remove(entity_qos_out_path)
                            os.remove(entity_diff_out_path)

                        if error_count > 0 and args.break_on_failure:
                            raise BreakLoop

                except NextProfile:
                    error_count += 1
                    if args.break_on_failure:
                        raise BreakLoop

        except BreakLoop:
            print('Stopping Test.')
            pass

        # Formatting
        if error_count > 0:
            print()

        print(f"Total errors: {error_count}\n")

if __name__ == "__main__":
    main()