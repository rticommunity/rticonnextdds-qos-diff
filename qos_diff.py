import os
import subprocess
import sys
import argparse
import shutil
import subprocess
import xml.etree.ElementTree as ET
import difflib

RTI_XML_UTILITY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'rticonnextdds-xml-output-utility/build/rtixmloutpututility')

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

    # Recursively search for all profiles
    for qos_library in root.findall('.//qos_library'):
        library_name = qos_library.get('name')
        if library_name:
            for qos_profile in qos_library.findall('.//qos_profile'):
                profile_name = qos_profile.get('name')
                if profile_name:
                    qos_profiles.add((f"{library_name}::{profile_name}", f"{library_name}::{profile_name}"))
    return qos_profiles

def compare_qos_files(profile_dir, tag, qos_profile):
    error_count = 0

    with open(os.path.join(profile_dir, f'{tag}_1.xml'), 'r') as file1, open(os.path.join(profile_dir, f'{tag}_2.xml'), 'r') as file2:
        file1_lines = file1.readlines()
        file2_lines = file2.readlines()

    # Perform diff and get the line count
    diff_lines = list(difflib.unified_diff(file1_lines, file2_lines, fromfile=f'{tag}_1.xml', tofile=f'{tag}_2.xml', lineterm=''))  # Convert the iterator to a list
    diff_line_count = len(diff_lines)

    # Write the diff to the file
    with open(os.path.join(profile_dir, f'{tag}.txt'), 'w') as diff_file:
        diff_file.writelines(diff_lines)

    if tag == 'domain_participant_qos':
        # diff_line_count will be 11 if process_id is only difference
        if diff_line_count != 11:
            print(f"Qos Failure | Profile: {qos_profile[1]} | Entity: {tag}")
            error_count += 1
    else:
        # Any difference in the profile is considered a failure
        if diff_line_count != 0:
            print(f"Qos Failure | Profile: {qos_profile[1]} | Entity: {tag}")
            error_count += 1

    return error_count

# Argument parser setup
parser = argparse.ArgumentParser(description='Diff two DDS QoS files. Two separate files or the same file from a previous Git commit can be diffed.')
parser.add_argument('--qos_file', type=str, required=True, help='Required argument. Specify the Qos file.')
parser.add_argument('--diff_file', type=str, default='', help='Specify a Qos file to diff.')
parser.add_argument('--commit', type=str, default='', help='Specify the Git commit hash of the base file.')
parser.add_argument('--profile', type=str, default='', help='Specify the Qos profile in the format: Library::Profile. Otherwise all profiles will be diffed.')
parser.add_argument('--new_profile', type=str, default='', help='If the profile has been renamed in the diff file, specify the new Qos Profile in the format: Library::Profile.')
parser.add_argument('--out_dir', type=str, default=os.path.join(os.getcwd(), 'output'), help='Output directory. Default is ${PWD}/output.')
parser.add_argument('--rm', action='store_true', help='Delete intermediary diff output.')
parser.add_argument('--break_on_failure', action='store_true', help='Break on diff failure.')
args = parser.parse_args()

# Delete previous output directory
if os.path.exists(args.out_dir):
    shutil.rmtree(args.out_dir)
os.makedirs(args.out_dir)

# Define Qos Files

# Specify the output file paths
base_qos = os.path.join(args.out_dir, 'base_qos.xml')
diff_qos = os.path.join(args.out_dir, 'diff_qos.xml')

# Check if the Qos file exists
if os.path.exists(args.qos_file) == False:
    print(f"Error: {args.qos_file} does not exist.")
    sys.exit(1)

if args.qos_file == 'USER_QOS_PROFILES.xml':
    print("Error: USER_QOS_PROFILES.xml can't be in the working directory when diff is called.  See README for more information.") # TODO make sure to add this to the README
    sys.exit(1)

if args.commit != '':
    repo_path = get_git_repo_root(args.qos_file)
    # Get the Base Qos file from the Git commit
    subprocess.run(['git', '-C', repo_path, 'show', f'{args.commit}:{os.path.relpath(args.qos_file, repo_path)}'], stdout=open(base_qos, 'w'))
    # Save the current Qos file as the Diff Qos file
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
# args.profile is not empty
elif args.new_profile != '':
    # Profile name has changed.  Diff a different profile
    qos_profiles.add((args.profile, args.new_profile))
else:
    # Profile name hasn't changed.  Diff the same profile
    qos_profiles.add((args.profile, args.profile))

# Create list of Qos entity tags to iterate on
tags = [
    'domain_participant_qos',
    'publisher_qos',
    'datawriter_qos',
    'subscriber_qos',
    'datareader_qos',
    'topic_qos'
]

error_count = 0

log_file_path = os.path.join(args.out_dir, 'log.txt')

# TODO: What if a profile is not found in one of the files?

print()
try:
    with open(log_file_path, 'a') as log_file:
        for qos_profile in qos_profiles:
            # TODO: Am I sure I want to use qos_profile[1] as the directory name?
            profile_dir = os.path.join(args.out_dir, qos_profile[1])
            os.makedirs(profile_dir)
            for tag in tags:
                # Generate combined XML Qos file
                subprocess.run([
                    RTI_XML_UTILITY_PATH,
                    '-qosFile', base_qos,
                    '-outputFile', os.path.join(profile_dir, f'{tag}_1.xml'),
                    '-qosProfile', f"{qos_profile[0]}",
                    '-qosTag', tag
                ], stdout=log_file, stderr=log_file)

                subprocess.run([
                    RTI_XML_UTILITY_PATH,
                    '-qosFile', diff_qos,
                    '-outputFile', os.path.join(profile_dir, f'{tag}_2.xml'),
                    '-qosProfile', f"{qos_profile[1]}",
                    '-qosTag', tag
                ], stdout=log_file, stderr=log_file)

                # Diff the two files
                error_count += compare_qos_files(profile_dir, tag, qos_profile)

                # Remove generated Qos files
                if args.rm:
                    os.remove(os.path.join(profile_dir, f'{tag}_1.xml'))
                    os.remove(os.path.join(profile_dir, f'{tag}_2.xml'))

                # Break loop if break_on_failure is set and there is an error
                if args.break_on_failure and error_count > 0:
                    raise BreakLoop

except BreakLoop:
    pass

# Formatting
if error_count > 0:
    print()

print(f"{error_count} errors detected.\n")