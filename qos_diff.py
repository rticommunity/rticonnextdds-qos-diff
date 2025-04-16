import os
import subprocess
import sys
import argparse
import shutil
import subprocess
from  utils import *
from QosDiff import *

# class NextProfile(Exception):
#     pass

# class BreakLoop(Exception):
#     pass

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

def parse_arguments():
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
    return parser.parse_args()

def main():
    args = parse_arguments()

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
        elif args.expand:
            shutil.copy(args.qos_file, qos_diff.base.path)
            shutil.copy(args.qos_file, qos_diff.diff.path)
        else:
            print("Error - Must specify either:\n",
                "Diff: --commit or --diff_file to diff a Qos file\n",
                "Expand: --expand to expand a Qos file\n")
            sys.exit(1)

        # Define the Profiles
        qos_diff.get_profiles(args.profile, args.new_profile)

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
            if args.expand:
                qos_diff.run_expand(log_file)
            else:
                cumulative_error_count += qos_diff.run_diff(log_file)
        except BreakLoop as e:
            cumulative_error_count += e.error_count
            print('\nTest Incomplete.  ', end='')
        except FileNotFoundError:
            print('Qos expansion failed.  Exiting...')
            sys.exit(1)

        if not args.expand:
            print(f"Total errors: {cumulative_error_count}\n")

if __name__ == "__main__":
    main()