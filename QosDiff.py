import logging
import os
import difflib
from  utils import *
from QosEntities import *

from QosDiffFile import QosDiffFile, QosType

logger = logging.getLogger(__name__)

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

    def get_profiles(self, profile_arg, new_profile_arg):
        def split_profile_arg(arg):
            parts = arg.split("::")
            if len(parts) not in (2, 4):
                logger.error(f"Input must have 2 or 4 parts separated by '::', Input: {arg!r}")
                raise ValueError(f"Input must have 2 or 4 parts separated by '::', Input: {arg!r}")
            library = parts[0]
            profile = parts[1]
            entity = parts[2] if len(parts) == 4 else None
            entity_type = parts[3].lower() if len(parts) == 4 else None
            try:
                enum_value = QosEntitiesEnum(entity_type) if len(parts) == 4 else None
                return QosEntityData(library, profile, entity, enum_value)
            except ValueError as e:
                logger.error(f"Invalid entity_type '{entity_type}' for QosEntitiesEnum.")
                raise e

        if not profile_arg and not new_profile_arg:
            base_qos_profiles = set()
            diff_qos_profiles = set()
            base_qos_profiles.update(find_qos_profiles(self.base.path))
            if not self.expand:
                diff_qos_profiles.update(find_qos_profiles(self.diff.path))

            self.qos_profiles = QosEntityData.join_sets(base_qos_profiles, diff_qos_profiles)
        else:
            base_profile = split_profile_arg(profile_arg)
            diff_profile = split_profile_arg(new_profile_arg) if new_profile_arg else base_profile
            self.qos_profiles.add((base_profile, diff_profile))

    def run_expand(self):
        for base_profile, _ in self.qos_profiles:
            profile = base_profile.join()
            print(f"Expanding Qos Profile: {profile}")
            curr_diff_dir = os.path.join(self.out_dir, profile)
            os.makedirs(curr_diff_dir)
            if base_profile.is_named_entity():
                # This is a named entity, only expand that one
                expand_qos_profile(self.base, curr_diff_dir, base_profile, base_profile.entity_type)
            else:
                for entity_type in QosEntitiesEnum:
                    # This is a generic profile, expand all entities
                    expand_qos_profile(self.base, curr_diff_dir, base_profile, entity_type)

    def run_diff(self):
        cumulative_error_count = 0

        for index, (base_profile, diff_profile) in enumerate(self.qos_profiles):
            error_count = 0
            try:
                # Name the folder after the new profile, if the names are different (index 1)
                current_profile_name = QosEntityData.get_common_profile_name((base_profile, diff_profile))
                print(f"Diffing Qos Profile: {current_profile_name}")
                curr_diff_dir = os.path.join(self.out_dir, current_profile_name)
                os.makedirs(curr_diff_dir)

                if base_profile.entity_type != diff_profile.entity_type:
                    logger.error(f"Entity type mismatch: {base_profile} vs {diff_profile}")
                    raise NextProfile("Mismatched entity types")

                named_entity_profile = base_profile.is_named_entity() or diff_profile.is_named_entity()
                for entity_type in QosEntitiesEnum:
                    # If a named entity profile, only expand/compare the matching entity type
                    if named_entity_profile and  diff_profile.entity_type != entity_type:
                        continue

                    expand_qos_profile(self.base, curr_diff_dir, base_profile, entity_type)
                    expand_qos_profile(self.diff, curr_diff_dir, diff_profile, entity_type)

                    error_count += self._compare_qos_files(curr_diff_dir, entity_type.value, (base_profile, diff_profile))

                    if self.rm:
                        os.remove(os.path.join(curr_diff_dir, self.base.get_entity_path(entity_type)))
                        os.remove(os.path.join(curr_diff_dir, self.diff.get_entity_path(entity_type)))

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