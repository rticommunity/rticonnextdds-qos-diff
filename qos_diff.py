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
import shutil
from pathlib import Path

from src.LogFormatter import ColorFormatter
from src.PrintColor import print_colored
from src.QosDiff import QosDiff, QosType
from src.QosDiffExceptions import BreakLoop
from src.Utilities import get_connext_versions, get_git_repo_root

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Diff two DDS QoS files. Two separate files or the same file from a previous Git commit can be diffed.')
    parser.add_argument('--qos_file', type=Path, nargs='+', required=True, help='Required argument. Specify one or more Qos files.')
    parser.add_argument('--diff_file', type=Path, nargs='*', default=[], help='Specify one or more Qos files to diff.')
    parser.add_argument('--commit', type=str, default='', help='Specify the Git commit hash of the base file.')
    parser.add_argument('--profile', type=str, default='', help='Specify the Qos profile as specified in the README. Otherwise all profiles will be diffed.')
    parser.add_argument('--new_profile', type=str, default='', help='If the profile has been renamed in the diff file, specify the new Qos Profile as specified in the README.')
    parser.add_argument('--out_dir', type=Path, default=Path.cwd() / 'output', help='Output directory. Default is ${CWD}/output.')
    parser.add_argument('--rm', action='store_true', help='Delete intermediary diff output.')
    parser.add_argument('--break_on_failure', action='store_true', help='Break on diff failure.')
    parser.add_argument('--versions', action='store_true', help='Diff against two different versions of Connext DDS.')
    parser.add_argument('--expand', action='store_true', help='Only expand profiles.  Do not diff.')
    parser.add_argument('--delta', action='store_true', help='Only show the delta from default profile values.')
    parser.add_argument('--ignore_nddshome', action='store_true', help='Ignore NDDSHOME as the default Connext version.')
    return parser.parse_args()

def setup_logging(out_dir: Path) -> logging.Logger:
    """Set up logging to file and console, return the configured logger."""
    log_path = out_dir / 'log.txt'
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('[%(asctime)s - %(levelname)s - %(name)s - Line: %(lineno)d] %(message)s'))
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(ColorFormatter('[%(levelname)s - %(name)s] %(message)s'))
    logger.addHandler(console_handler)

    return logger

def main() -> None:

    args = parse_arguments()

    # Delete previous output directory
    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(args.out_dir)

    # Log all command-line arguments
    logger.debug("Command-line arguments:")
    for arg, value in vars(args).items():
        logger.debug(f"{arg}: {value}")

    # Check if the Qos file exists
    for qos_file in args.qos_file + args.diff_file:
        if not qos_file.exists():
            logger.error(f"Error: {qos_file} does not exist.")
            sys.exit(1)

    # Initialize the QosDiff object with the provided arguments
    qos_diff = QosDiff(args)

    # Logic to determine the base and diff files based on the provided arguments
    if args.commit:
        repo_path = get_git_repo_root(args.qos_file[0])
        for qos_file in args.qos_file:
            # Get the path to store the base file pulled from Git
            base_profile_path = qos_diff.build_qos_file_path(qos_file, QosType.BASE)
            with open(base_profile_path, 'w') as base_file:
                file_rel_path = qos_file.resolve().relative_to(repo_path.resolve()).as_posix()
                arguments = ['git', '-C', str(repo_path), 'show', f'{args.commit}:{file_rel_path}']
                logger.debug(f"Retrieving file from git: {' '.join(arguments)}")
                result = subprocess.run(
                    arguments,
                    stdout=base_file,
                    stderr=subprocess.PIPE
                )
                if result.returncode != 0:
                    logger.error("Error: Failed to get the base QoS file from the Git commit. See README for details.")
                    logger.error(result.stderr.decode())
                    sys.exit(1)
            # Store the file pulled from Git as the base file and the current file as the diff file
            qos_diff.add_qos_file(base_profile_path, QosType.BASE)
            # Copy the existing into the expected location
            qos_diff.copy_qos_file(qos_file, QosType.DIFF)
    elif args.diff_file is not None:
        for file in args.qos_file:
            qos_diff.copy_qos_file(file, QosType.BASE)
        for file in args.diff_file:
            qos_diff.copy_qos_file(file, QosType.DIFF)
    elif args.expand:
        for file in args.qos_file:
            qos_diff.copy_qos_file(file, QosType.BASE)
        # There will not be any DIFF files in expand mode
    else:
        logger.error("Error - Must specify either:\nDiff: --commit or --diff_file to diff a Qos file\nExpand: --expand to expand a Qos file")
        sys.exit(1)

    # USER_QOS_PROFILES.xml can't be in the working directory when diff is called.  Move up a directory.
    if (any(f.name == 'USER_QOS_PROFILES.xml' for f in args.qos_file)
    or any(f.name == 'USER_QOS_PROFILES.xml' for f in args.diff_file)):
        os.chdir('..')

    # Prompt the user to select the version of Connext for processing
    get_connext_versions(qos_diff, args)

    # Walk the Qos files to enumerate all profiles
    qos_diff.get_profiles(args.profile, args.new_profile)

    cumulative_error_count = 0
    print()
    try:
        if args.expand:
            qos_diff.run_expand()
        else:
            cumulative_error_count += qos_diff.run_diff()
    except BreakLoop as e:
        cumulative_error_count += e.error_count
        print('\nTest Incomplete.  ', end='')
    except FileNotFoundError:
        logger.error('Qos expansion failed.  Exiting...')
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