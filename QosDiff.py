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
            if len(parts) not in (2, 5):
                logger.error(f"Input must have 2 or 5 parts separated by '::', Input: {arg!r}")
                raise ValueError(f"Input must have 2 or 5 parts separated by '::', Input: {arg!r}")
            library = parts[0]
            profile = parts[1]
            entity_name = parts[2] if len(parts) == 5 else None
            topic_filter = parts[3] if len(parts) == 5 else None
            entity_type = parts[4].lower() if len(parts) == 5 else None
            try:
                enum_value = QosEntitiesEnum(entity_type) if len(parts) == 5 else None
                return QosEntityData(library, profile, entity_name, topic_filter, enum_value)
            except ValueError as e:
                logger.error(f"Invalid entity_type '{entity_type}' for QosEntitiesEnum.")
                raise e

        if not profile_arg and not new_profile_arg:
            base_qos_profiles = set()
            diff_qos_profiles = set()
            base_qos_profiles.update(find_qos_profiles(self.base))
            if not self.expand:
                diff_qos_profiles.update(find_qos_profiles(self.diff))

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
            if base_profile.has_topic_filter():
                # This has a topic filter, only expand that one
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

                named_entity_profile = base_profile.has_topic_filter() or diff_profile.has_topic_filter()
                for entity_type in QosEntitiesEnum:
                    # If a named entity profile, only expand/compare the matching entity type
                    if named_entity_profile and  diff_profile.entity_type != entity_type:
                        continue

                    expand_qos_profile(self.base, curr_diff_dir, base_profile, entity_type)
                    expand_qos_profile(self.diff, curr_diff_dir, diff_profile, entity_type)

                    error_count += self._compare_qos_files(curr_diff_dir, entity_type, (base_profile, diff_profile))

                    if self.rm:
                        os.remove(os.path.join(curr_diff_dir, self.base.get_entity_path(entity_type)))
                        os.remove(os.path.join(curr_diff_dir, self.diff.get_entity_path(entity_type)))

                    if error_count > 0 and self.break_on_failure:
                        cumulative_error_count += error_count
                        raise BreakLoop(cumulative_error_count)

            except NextProfile:
                cumulative_error_count += 1
                if self.break_on_failure:
                    raise BreakLoop(cumulative_error_count)
                else:
                    print()

            cumulative_error_count += error_count
            if (error_count > 0) or (index == len(self.qos_profiles) - 1):
                print()

        return cumulative_error_count

    def _compare_qos_files(self, profile_dir: str, entity_type: QosEntitiesEnum, qos_profile: tuple[QosEntityData, QosEntityData]) -> int:
        error_count = 0
        base_profile, diff_profile = qos_profile

        try:
            with open(os.path.join(profile_dir, f'{entity_type.value}_base.xml'), 'r') as file1, open(os.path.join(profile_dir, f'{entity_type.value}_diff.xml'), 'r') as file2:
                file1_lines = file1.readlines()
                file2_lines = file2.readlines()

            # Perform diff and get the line count, convert the iterator to a list
            diff_lines = list(difflib.unified_diff(file1_lines, file2_lines, fromfile=f'{entity_type.value}_base.xml', tofile=f'{entity_type.value}_diff.xml', lineterm=''))
            diff_line_count = len(diff_lines)

            # Write the diff to the file
            with open(os.path.join(profile_dir, f'{entity_type.value}_result.txt'), 'w') as diff_file:
                diff_file.writelines(diff_lines)

            if entity_type == QosEntitiesEnum.DOMAIN_PARTICIPANT:
                # diff_line_count will be 11 if process_id is only difference
                if diff_line_count != 11:
                    print(f"Qos Failure | Profile: {base_profile.join()} | Entity: {entity_type.name}")
                    error_count += 1
            else:
                # Any difference in the profile is considered a failure
                if diff_line_count != 0:
                    print(f"Qos Failure | Profile: {diff_profile.join()} | Entity: {entity_type.name}")
                    error_count += 1
        except FileNotFoundError as e:
            logger.error(f"Diff Error: {e}")
            diff_missing = ('_diff.xml' in e.filename)
            profiles_equal = (base_profile == diff_profile)

            # Choose which profile to reference
            profile = base_profile if profiles_equal or not diff_missing else diff_profile
            # Choose which file type
            file_type = "diff" if diff_missing else "base"
            logger.error(f"Error: {profile.join()} not found in the {file_type} Qos file.")

            raise NextProfile

        return error_count