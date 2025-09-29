import os
import sys
from enum import IntEnum
import difflib
from  utils import *

ENTITIES = ['domain_participant_qos', 'publisher_qos', 'datawriter_qos', 'subscriber_qos', 'datareader_qos', 'topic_qos']

class QosType(IntEnum):
    BASE = 0
    DIFF = 1

class QosDiffFile:
    def __init__(self, out_dir, type):
        self.type = type
        self.path = os.path.join(out_dir, 'base_qos.xml' if self.type == QosType.BASE else 'diff_qos.xml')
        self.version = ''

    def get_entity_path(self, entity_name):
        return f'{entity_name}_base.xml' if self.type == QosType.BASE else f'{entity_name}_diff.xml'

class QosDiff:
    def __init__(self, args):
        self.out_dir = args.out_dir
        self.base = QosDiffFile(args.out_dir, QosType.BASE)
        self.diff = QosDiffFile(args.out_dir, QosType.DIFF)
        self.rm = args.rm
        self.break_on_failure = args.break_on_failure
        self.expand = args.expand

        # Define the Profiles
        self.qos_profiles = set()

    def get_profiles(self, profile, new_profile):
        base_qos_profiles = set()
        diff_qos_profiles = set()
        if profile == '' and new_profile == '':
            base_qos_profiles.update(find_qos_profiles(self.base.path))
            if not self.expand:
                diff_qos_profiles.update(find_qos_profiles(self.diff.path))
        else:
            if "::" in profile:
                library, profile = profile.split("::")
            else:
                # TODO: Figure out where this will get handled
                raise ValueError("Profile must be in the format 'library::profile'")

            if new_profile != '':
                if "::" in new_profile:
                    new_library, new_profile = new_profile.split("::")
                else:
                    # TODO: Figure out where this will get handled
                    raise ValueError("New profile must be in the format 'library::profile'")
                base_qos_profiles.add(QosEntityData(library, profile, None))
                diff_qos_profiles.add(QosEntityData(new_library, new_profile, None))
            else:
                base_qos_profiles.add(QosEntityData(library, profile, None))
                diff_qos_profiles.add(QosEntityData(library, profile, None))

        self.qos_profiles = QosEntityData.join_sets(base_qos_profiles, diff_qos_profiles)

    def run_expand(self, log_file=sys.stdout):
        # Map dictionary keys → qos type strings
        qos_type_map = {
                "writers": "datawriter_qos",
                "readers": "datareader_qos",
                "topics": "topic_qos",
            }

        for qos_profile in self.qos_profiles:
            print(f"Expanding Qos Profile: {qos_profile[QosType.BASE].join()}")
            curr_diff_dir = os.path.join(self.out_dir, qos_profile[QosType.BASE].join())
            os.makedirs(curr_diff_dir)
            for entity in ENTITIES:
                expand_qos_profile(self.base, curr_diff_dir, qos_profile[QosType.BASE].join(), entity, log_file)

            entities = find_named_entities_in_profile(qos_profile[QosType.BASE])

            for entity_type, names in entities.items():
                qos_type_str = qos_type_map[entity_type]
                for name in names:
                    profile_name = qos_profile[QosType.BASE].join_with_entity_name(name)
                    print(f"Expanding Qos Profile: {profile_name}")

                    curr_diff_dir = os.path.join(self.out_dir, profile_name)
                    os.makedirs(curr_diff_dir, exist_ok=True)

                    expand_qos_profile(
                        self.base,
                        curr_diff_dir,
                        qos_profile[QosType.BASE].join(),
                        qos_type_str,
                        log_file,
                        entity_name=name
                    )

    def run_diff(self, log_file=sys.stdout):
        cumulative_error_count = 0

        for index, qos_profile in enumerate(self.qos_profiles):
            error_count = 0
            try:
                # Name the folder after the new profile, if the names are different (index 1)
                current_profile_name = QosEntityData.get_common_profile_name(qos_profile)
                print(f"Diffing Qos Profile: {current_profile_name}")
                curr_diff_dir = os.path.join(self.out_dir, current_profile_name)
                os.makedirs(curr_diff_dir)
                for entity in ENTITIES:
                    expand_qos_profile(self.base, curr_diff_dir, qos_profile[0].join(), entity, log_file)
                    expand_qos_profile(self.diff, curr_diff_dir, qos_profile[1].join(), entity, log_file)

                    error_count += self._compare_qos_files(curr_diff_dir, entity, qos_profile)

                    if self.rm:
                        os.remove(os.path.join(curr_diff_dir, self.base.get_entity_path(entity)))
                        os.remove(os.path.join(curr_diff_dir, self.diff.get_entity_path(entity)))

                    if error_count > 0 and self.break_on_failure:
                        cumulative_error_count += error_count
                        raise BreakLoop(cumulative_error_count)

                # TODO: Look for named writers/readers/topics in the profile and expand/compare those as well

            except NextProfile:
                cumulative_error_count += 1
                if self.break_on_failure:
                    raise BreakLoop(cumulative_error_count)
                else:
                    print()

            cumulative_error_count += error_count
            # TODO: Unsure if adding named writers/readers/topics would need a different handling here
            if (error_count > 0) or (index == len(self.qos_profiles) - 1):
                print()

        return cumulative_error_count

    def _compare_qos_files(self, profile_dir, entity, qos_profile):
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
                    print(f"Qos Failure | Profile: {qos_profile[1].join()} | Entity: {entity}")
                    error_count += 1
            else:
                # Any difference in the profile is considered a failure
                if diff_line_count != 0:
                    print(f"Qos Failure | Profile: {qos_profile[1].join()} | Entity: {entity}")
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