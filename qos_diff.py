import os
import subprocess
import sys

RTI_XML_UTILITY_PATH = 'rticonnextdds-xml-output-utility/build'
OUT_DIR = 'output'

# Set environment variables
env_vars = {}
with open('env_vars.sh') as f:
    for line in f:
        if line.strip() and not line.startswith('#'):
            key, value = line.strip().split('=')
            env_vars[key] = value

# Verify environment variables have been set
if 'ENV_SET' not in env_vars:
    print("Environment variables not set.")
    sys.exit(1)

if os.path.exists(OUT_DIR):
    subprocess.run(['rm', '-r', OUT_DIR])
os.makedirs(OUT_DIR)

###############################################################################
# Create copy of original Qos file for diff

# Commit set, diff against previous version
if 'BASE_COMMIT' in env_vars:
    repo_path = env_vars['REPO_PATH']
    qos_file = env_vars['QOS_FILE']
    base_commit = env_vars['BASE_COMMIT']
    base_qos_path = os.path.join(OUT_DIR, 'base_qos.xml')
    diff_qos_path = os.path.join(OUT_DIR, 'diff_qos.xml')
    subprocess.run(['git', '-C', repo_path, 'show', f'{base_commit}:{qos_file[len(repo_path)+1:]}'], stdout=open(base_qos_path, 'w'))
    subprocess.run(['cp', qos_file, diff_qos_path])
else:
    subprocess.run(['cp', env_vars['QOS_FILE'], os.path.join(OUT_DIR, 'base_qos.xml')])
    subprocess.run(['cp', env_vars['DIFF_QOS_FILE'], os.path.join(OUT_DIR, 'diff_qos.xml')])

QOS_1 = os.path.join(OUT_DIR, 'base_qos.xml')
QOS_2 = os.path.join(OUT_DIR, 'diff_qos.xml')

if len(sys.argv) == 2:
    PROFILES = [sys.argv[1]]
else:
    with open(env_vars['PROFILE_LIST']) as f:
        PROFILES = [line.strip() for line in f]

###############################################################################

TAGS = [
    'domain_participant_qos',
    'publisher_qos',
    'datawriter_qos',
    'subscriber_qos',
    'datareader_qos',
    'topic_qos'
]

for PROFILE in PROFILES:
    profile_dir = os.path.join(OUT_DIR, PROFILE)
    os.makedirs(profile_dir)
    for TAG in TAGS:
        # Generate combined XML Qos file
        subprocess.run([
            os.path.join(RTI_XML_UTILITY_PATH, 'rtixmloutpututility'),
            '-qosFile', QOS_1,
            '-outputFile', os.path.join(profile_dir, f'{TAG}_1.xml'),
            '-qosProfile', f"{env_vars['QOS_LIBRARY']}::{PROFILE}",
            '-qosTag', TAG
        ])

        subprocess.run([
            os.path.join(RTI_XML_UTILITY_PATH, 'rtixmloutpututility'),
            '-qosFile', QOS_2,
            '-outputFile', os.path.join(profile_dir, f'{TAG}_2.xml'),
            '-qosProfile', f"{env_vars['QOS_LIBRARY']}::{PROFILE}",
            '-qosTag', TAG
        ])

        # -s = Identify identical files, -U unified context
        with open(os.path.join(profile_dir, f'{TAG}.txt'), 'w') as diff_file:
            subprocess.run([
                'diff', '-s', '-U', '1',
                os.path.join(profile_dir, f'{TAG}_1.xml'),
                os.path.join(profile_dir, f'{TAG}_2.xml')
            ], stdout=diff_file)

        # Remove generated Qos files (may want to keep these pending use case)
        os.remove(os.path.join(profile_dir, f'{TAG}_1.xml'))
        os.remove(os.path.join(profile_dir, f'{TAG}_2.xml'))

        if TAG == 'domain_participant_qos':
            # LINE_COUNT will be 7 if process_id is only difference
            with open(os.path.join(profile_dir, f'{TAG}.txt')) as f:
                LINE_COUNT = sum(1 for _ in f)
            if LINE_COUNT != int(env_vars['EXPECTED_DIFF_LINE_COUNT']):
                print(f"\nQos Failure | Profile: {PROFILE} | Entity: {TAG}\n")
                if int(env_vars['BREAK_ON_FAILURE']) == 1:
                    sys.exit(1)
        else:
            # If "identical" is not found, there is a difference
            with open(os.path.join(profile_dir, f'{TAG}.txt')) as f:
                if 'identical' not in f.read():
                    print(f"\nQos Failure | Profile: {PROFILE} | Entity: {TAG}\n")
                    if int(env_vars['BREAK_ON_FAILURE']) == 1:
                        sys.exit(1)
        print()

if int(env_vars['BREAK_ON_FAILURE']) == 1:
    print("No errors detected!\n")
else:
    print("Errors Detected:")
    subprocess.run(['grep', '-l', '---', '-r', '--exclude=*domain_participant_qos.txt', OUT_DIR])