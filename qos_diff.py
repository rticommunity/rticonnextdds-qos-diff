import os
import subprocess
import sys
import argparse
import shutil
import subprocess
import difflib
from  utils import *
from QosDiff import *

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

def compare_qos_files(profile_dir, entity, qos_profile):
    error_count = 0

    try:
        with open(os.path.join(profile_dir, f'{entity}_base.xml'), 'r') as file1, open(os.path.join(profile_dir, f'{entity}_diff.xml'), 'r') as file2:
            file1_lines = file1.readlines()
            file2_lines = file2.readlines()

        # Perform diff and get the line count, convert the iterator to a list
        diff_lines = list(difflib.unified_diff(file1_lines, file2_lines, fromfile=f'{entity}_base.xml', tofile=f'{entity}_diff.xml', lineterm=''))
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
        raise NextProfile

    return error_count

def expand_qos_profile(qos_file, diff_path, qos_profile, entity, log_file):
    subprocess.run([
        os.path.join(RTI_XML_UTILITY_PATH, 'build', qos_file.version, 'rtixmloutpututility'),
        '-qosFile', qos_file.path,
        '-outputFile', os.path.join(diff_path, qos_file.get_entity_path(entity)),
        '-qosProfile', qos_profile[qos_file.type.value],
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
    parser.add_argument('--expand', action='store_true', help='Fully expand all profiles.  Do not diff.')
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
        # qos_diff.base = QosDiffFile(args.out_dir, QosType.BASE)
        # qos_diff.diff = QosDiffFile(args.out_dir, QosType.DIFF)

        # Check if the Qos file exists
        if not os.path.exists(args.qos_file):
            print(f"Error: {args.qos_file} does not exist.")
            sys.exit(1)

        qos_diff = QosDiff(args)

        if args.commit != '':
            repo_path = get_git_repo_root(args.qos_file)
            result = subprocess.run(
                ['git', '-C', repo_path, 'show', f'{args.commit}:{os.path.relpath(args.qos_file, repo_path)}'],
                stdout=open(qos_diff.base.path, 'w'),
                stderr=log_file
            )
            if result.returncode != 0:
                print(f"Error: Failed to get the base QoS file from the Git commit. See README for details.")
                sys.exit(1)
            shutil.copy(args.qos_file, qos_diff.diff.path)
        elif args.diff_file != '':
            shutil.copy(args.qos_file, qos_diff.base.path)
            shutil.copy(args.diff_file, qos_diff.diff.path)
        else:
            print("Error: Must specify either --commit or --diff_file.")
            sys.exit(1)

        # # Define the Profiles
        qos_diff.get_profiles(args.profile, args.new_profile)

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
            qos_diff.base.version = select_option(connext_installations)
            print('\nPlease select a Connext version for the diff Qos file.')
            qos_diff.diff.version = select_option(connext_installations)
        else:
            print('Please select a Connext version to use.')
            qos_diff.base.version = select_option(connext_installations)
            qos_diff.diff.version = qos_diff.base.version
        print()

        cumulative_error_count = 0
        try:
            for index, qos_profile in enumerate(qos_diff.qos_profiles):
                error_count = 0
                try:
                    # Name the folder after the new profile, if the names are different (index 1)
                    print(f"Diffing Qos Profile: {qos_profile[1]}")
                    curr_diff_dir = os.path.join(args.out_dir, qos_profile[1])
                    os.makedirs(curr_diff_dir)
                    for entity in entities:
                        expand_qos_profile(qos_diff.base, curr_diff_dir, qos_profile, entity, log_file)
                        expand_qos_profile(qos_diff.diff, curr_diff_dir, qos_profile, entity, log_file)

                        error_count += compare_qos_files(curr_diff_dir, entity, qos_profile)

                        if args.rm:
                            os.remove(os.path.join(curr_diff_dir, qos_diff.base.get_entity_path(entity)))
                            os.remove(os.path.join(curr_diff_dir, qos_diff.diff.get_entity_path(entity)))

                        if error_count > 0 and args.break_on_failure:
                            cumulative_error_count += error_count
                            raise BreakLoop

                except NextProfile:
                    cumulative_error_count += 1
                    if args.break_on_failure:
                        raise BreakLoop
                    else:
                        print()

                cumulative_error_count += error_count
                if (error_count > 0) or (index == len(qos_diff.qos_profiles) - 1):
                    print()
        except BreakLoop:
            print('\nTest Incomplete.  ', end='')

        print(f"Total errors: {cumulative_error_count}\n")

if __name__ == "__main__":
    main()