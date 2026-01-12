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
import shutil
import logging

from src.Utilities import *
from src.QosDiff import *
from src.LogFormatter import ColorFormatter
from src.PrintColor import print_colored

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
                print_colored(logging.WARNING, "Exiting", "No diff will be performed.")
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
    parser.add_argument('--profile', type=str, default='', help='Specify the Qos profile as specified in the README. Otherwise all profiles will be diffed.')
    parser.add_argument('--new_profile', type=str, default='', help='If the profile has been renamed in the diff file, specify the new Qos Profile as specified in the README.')
    parser.add_argument('--out_dir', type=str, default=os.path.join(os.getcwd(), 'output'), help='Output directory. Default is ${CWD}/output.')
    parser.add_argument('--rm', action='store_true', help='Delete intermediary diff output.')
    parser.add_argument('--break_on_failure', action='store_true', help='Break on diff failure.')
    parser.add_argument('--versions', action='store_true', help='Diff against two different versions of Connext DDS.')
    parser.add_argument('--expand', action='store_true', help='Only expand profiles.  Do not diff.')
    parser.add_argument('--delta', action='store_true', help='Only show the delta from default profile values.')
    parser.add_argument('--ignore_nddshome', action='store_true', help='Ignore NDDSHOME as the default Connext version.')
    return parser.parse_args()

def main():
    args = parse_arguments()

    # Delete previous output directory
    if os.path.exists(args.out_dir):
        shutil.rmtree(args.out_dir)
    os.makedirs(args.out_dir)

    log_path = os.path.join(args.out_dir, 'log.txt')

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set root logger to lowest level you want

    # File handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] %(message)s'))
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(ColorFormatter('[%(levelname)s - %(name)s] %(message)s'))
    logger.addHandler(console_handler)

    # Log all command-line arguments
    logger.debug("Command-line arguments:")
    for arg, value in vars(args).items():
        logger.debug(f"{arg}: {value}")

    # Check if the Qos file exists
    if not os.path.exists(args.qos_file):
        logger.error(f"Error: {args.qos_file} does not exist.")
        sys.exit(1)

    qos_diff = QosDiff(args)

    if args.commit:
        repo_path = get_git_repo_root(args.qos_file)
        with open(qos_diff.base.path, 'w') as base_file:
            result = subprocess.run(
                ['git', '-C', repo_path, 'show', f'{args.commit}:{os.path.relpath(args.qos_file, repo_path)}'],
                stdout=base_file,
                stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                logging.error("Error: Failed to get the base QoS file from the Git commit. See README for details.")
                logging.error(result.stderr.decode())
                sys.exit(1)
        shutil.copy(args.qos_file, qos_diff.diff.path)
    elif args.diff_file:
        shutil.copy(args.qos_file, qos_diff.base.path)
        shutil.copy(args.diff_file, qos_diff.diff.path)
    elif args.expand:
        shutil.copy(args.qos_file, qos_diff.base.path)
    else:
        logging.error("Error - Must specify either:\nDiff: --commit or --diff_file to diff a Qos file\nExpand: --expand to expand a Qos file")
        sys.exit(1)

    # USER_QOS_PROFILES.xml can't be in the working directory when diff is called.  Move up a directory.
    if args.qos_file == 'USER_QOS_PROFILES.xml' or args.diff_file == 'USER_QOS_PROFILES.xml':
        os.chdir('..')

    connext_installations = find_rti_connext_dds_dirs(os.path.join(RTI_XML_UTILITY_PATH, 'build'))
    nddshome = os.environ.get("NDDSHOME")
    env_connext_dir = (
        os.path.basename(nddshome)
        if nddshome and os.path.basename(nddshome).startswith("rti_connext_dds-")
        else None
    )

    if not connext_installations:
        logging.error("Error: No RTI Connext DDS installations found.")
        sys.exit(1)

    if(args.versions):
        if len(connext_installations) < 2:
            logging.error("Error: Two RTI Connext DDS installations are required to diff versions.")
            sys.exit(1)
        print('Please select a Connext version for the baseline Qos file:')
        qos_diff.base.version = select_option(connext_installations)
        print('\nPlease select a Connext version for the diff Qos file:')
        qos_diff.diff.version = select_option(connext_installations)
    elif env_connext_dir in connext_installations and not args.ignore_nddshome:
        qos_diff.base.version = qos_diff.diff.version = env_connext_dir
    else:
        if len(connext_installations) > 1:
            print('Please select a Connext version to use:')
            qos_diff.base.version = qos_diff.diff.version = select_option(connext_installations)
        else:
            qos_diff.base.version = qos_diff.diff.version = next(iter(connext_installations))

    logger.debug(f"Base version: {qos_diff.base.version}, Diff version: {qos_diff.diff.version}")
    if args.delta and not args.expand:
        print("Warning: --delta only applies when --expand is also specified.  Ignoring --delta.\n")

    # Define the Profiles
    qos_diff.get_profiles(args.profile, args.new_profile)

    cumulative_error_count = 0
    print()
    try:
        if args.expand:
            qos_diff.run_expand(args.delta)
        else:
            cumulative_error_count += qos_diff.run_diff()
    except BreakLoop as e:
        cumulative_error_count += e.error_count
        print('\nTest Incomplete.  ', end='')
    except FileNotFoundError:
        logging.error('Qos expansion failed.  Exiting...')
        sys.exit(1)

    if not args.expand:
        logger.info(f"Total errors: {cumulative_error_count}")
        if cumulative_error_count:
            error_str = f"{cumulative_error_count} Diff Error" + ("s" if cumulative_error_count > 1 else "")
            print_colored(logging.ERROR, "Test Failure", error_str)
        else:
            print_colored(logging.INFO, "Test Pass", "No Diff Errors")

if __name__ == "__main__":
    main()