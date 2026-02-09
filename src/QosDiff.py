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

import logging
import difflib
import platform
import shutil
import subprocess
from pathlib import Path

from src.QosDiffConstants import RTI_XML_UTILITY_PATH, QosEntitiesEnum, QosType
from src.SearchProfiles import find_qos_profiles
from src.QosDiffExceptions import NextProfile, BlankProfile, BreakLoop
from src.QosEntityData import QosEntityData
from src.PrintColor import print_colored

logger = logging.getLogger(__name__)

class QosVersion:
    def __init__(self):
        self.base_version = ''
        self.diff_version = ''

    def set_version(self, version: str, qos_type: QosType):
        if qos_type == QosType.BASE:
            self.base_version = version
        else:
            self.diff_version = version

    def get_version(self, qos_type: QosType) -> str:
        return self.base_version if qos_type == QosType.BASE else self.diff_version
    
class NddsQosProfiles:
    def __init__(self):
        self.base_profiles = []
        self.diff_profiles = []
        self.base_profiles_str = None
        self.diff_profiles_str = None

    def finalize_profiles(self):
        def join_paths(paths: list[Path]) -> str | None:
            if len(paths) > 0:
                # return "'" + ";".join(str(p) for p in paths) + "'"
                return ";".join(str(p) for p in paths)
            else:
                return None
        self.base_profiles_str = join_paths(self.base_profiles)
        self.diff_profiles_str = join_paths(self.diff_profiles)

    def add_qos_files(self, qos_file: Path, qos_type: QosType):
        if qos_type == QosType.BASE:
            self.base_profiles.append(qos_file)
        else:
            self.diff_profiles.append(qos_file)
    
    def get_file_str(self, qos_type: QosType) -> str:
        if self.base_profiles_str is None and self.diff_profiles_str is None:
            self.finalize_profiles()
        return self.base_profiles_str if qos_type == QosType.BASE else self.diff_profiles_str

class QosDiff:
    def __init__(self, args):
        self.out_dir = args.out_dir
        self.rm = args.rm
        self.break_on_failure = args.break_on_failure
        self.expand = args.expand
        self.delta = args.delta
        self.connext_version = QosVersion()
        # Define the Profiles
        self.qos_profiles = []
        # TODO: Remove List later
        self.qos_files = NddsQosProfiles()

    def build_qos_file_path(self, qos_file: Path, qos_type: QosType) -> Path:
        return self.out_dir / (qos_file.stem + '_' + qos_type.name.lower() + '_qos.xml')

    def copy_qos_file(self, source_file: Path, qos_type: QosType):
        new_path = self.build_qos_file_path(source_file, qos_type)
        shutil.copy(source_file, new_path)
        self.qos_files.add_qos_files(new_path, qos_type)

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

        qos_profiles = set()
        if not profile_arg and not new_profile_arg:
            base_qos_profiles = set()
            diff_qos_profiles = set()
            for file in self.qos_files.base_profiles:
                base_qos_profiles.update(find_qos_profiles(file, QosType.BASE))
            if not self.expand:
                for file in self.qos_files.diff_profiles:
                    diff_qos_profiles.update(find_qos_profiles(file, QosType.DIFF))

            qos_profiles = QosEntityData.join_sets(base_qos_profiles, diff_qos_profiles)
        else:
            base_profile = split_profile_arg(profile_arg)
            diff_profile = split_profile_arg(new_profile_arg) if new_profile_arg else base_profile
            qos_profiles.add((base_profile, diff_profile))

        self.qos_profiles = list(qos_profiles)
        self.qos_profiles.sort(key=lambda x: QosEntityData.get_common_profile_name(x))

    def run_expand(self):
        for base_profile, _ in self.qos_profiles:
            profile = base_profile.join()
            print(f"Expanding Qos Profile: {profile}")
            curr_diff_dir = self.out_dir / profile
            if platform.system() == 'Windows':
                curr_diff_dir = Path(str(curr_diff_dir).replace("::", "__"))
            curr_diff_dir.mkdir(parents=True, exist_ok=True)
            if base_profile.has_topic_filter():
                # This has a topic filter, only expand that one
                self.expand_qos_profile(QosType.BASE, curr_diff_dir, base_profile, base_profile.entity_type)
            else:
                for entity_type in QosEntitiesEnum:
                    # This is a generic profile, expand all entities
                    self.expand_qos_profile(QosType.BASE, curr_diff_dir, base_profile, entity_type)

    def run_diff(self):
        cumulative_error_count = 0

        for base_profile, diff_profile in self.qos_profiles:
            error_count = 0
            try:
                # Name the folder after the new profile, if the names are different (index 1)
                current_profile_name = QosEntityData.get_common_profile_name((base_profile, diff_profile))
                print(f"Diffing Qos Profile: {current_profile_name}")
                if base_profile.is_default() or diff_profile.is_default():
                    error_count += 1

                    if base_profile.is_default():
                        warning_string = (
                            f"Profile {current_profile_name} is missing in the base Qos file. "
                            "Only expanding the diff profile."
                        )
                    else:  # diff_profile.is_default()
                        warning_string = (
                            f"Profile {current_profile_name} is missing in the diff Qos file. "
                            "Only expanding the base profile."
                        )

                    logger.debug(warning_string)
                    print_colored(logging.WARNING, "Empty Profile", warning_string)

                curr_diff_dir = self.out_dir / current_profile_name
                if platform.system() == 'Windows':
                    curr_diff_dir = Path(str(curr_diff_dir).replace("::", "__"))
                curr_diff_dir.mkdir(parents=True, exist_ok=True)

                if base_profile.entity_type != diff_profile.entity_type:
                    logger.error(f"Entity type mismatch: {base_profile} vs {diff_profile}")
                    raise NextProfile("Mismatched entity types")

                named_entity_profile = base_profile.has_topic_filter() or diff_profile.has_topic_filter()
                for entity_type in QosEntitiesEnum:
                    # If a named entity profile, only expand/compare the matching entity type
                    if named_entity_profile and  diff_profile.entity_type != entity_type:
                        continue

                    # Expand both QoS files regardless if a BlankProfile is found, raise any other exceptions
                    exceptions = []
                    for args in [
                            (QosType.BASE, curr_diff_dir, base_profile, entity_type),
                            (QosType.DIFF, curr_diff_dir, diff_profile, entity_type)]:
                        try:
                            self.expand_qos_profile(*args)
                        except Exception as e:
                            exceptions.append(e)
                            if isinstance(e, BlankProfile):
                                logger.debug(f"Blank profile encountered for entity type: {entity_type.name}")
                            else:
                                logger.error(f"Error expanding QoS profile for {args[2]}: {e}")
                                raise e

                    # After both calls:
                    non_blank_exceptions = [e for e in exceptions if not isinstance(e, BlankProfile)]

                    if non_blank_exceptions:
                        # raise the first non-BlankProfile exception
                        raise non_blank_exceptions[0]
                    elif exceptions:
                        # Only BlankProfile errors occurred, move on to next entity.  No sense in comparing.
                        continue

                    error_count += self._compare_qos_files(curr_diff_dir, entity_type, (base_profile, diff_profile))

                    if self.rm:
                        # TODO: Test this.
                        (curr_diff_dir / self.create_entity_path(QosType.BASE, entity_type)).unlink()
                        (curr_diff_dir / self.create_entity_path(QosType.DIFF, entity_type)).unlink()

                    if error_count > 0 and self.break_on_failure:
                        cumulative_error_count += error_count
                        raise BreakLoop(cumulative_error_count)

            except NextProfile:
                cumulative_error_count += 1
                if self.break_on_failure:
                    raise BreakLoop(cumulative_error_count)

            if error_count == 0:
                print_colored(logging.INFO, "Success", f"Profile: {current_profile_name}\n")
            else:
                print_colored(logging.ERROR, "Failure", f"Profile: {current_profile_name}\n")
                cumulative_error_count += error_count

        return cumulative_error_count

    def _compare_qos_files(self, profile_dir: Path, entity_type: QosEntitiesEnum, qos_profile: tuple[QosEntityData, QosEntityData]) -> int:
        def remove_trigger_lines(lines: list[str]) -> list[str]:
            """
            If a line contains any trigger string, the following line is removed.
            """
            # These are properties that will always differ and should be ignored in the diff
            TRIGGER_STRINGS = [
                "<name>dds.sys_info.process_id</name>",
                "<name>dds.sys_info.executable_filepath</name>",
                "<name>dds.sys_info.creation_timestamp</name>",
                "<name>dds.sys_info.execution_timestamp</name>"
            ]

            cleaned = []
            skip_next = False

            for i, line in enumerate(lines):
                if skip_next:
                    skip_next = False
                    continue

                if any(t in line for t in TRIGGER_STRINGS):
                    cleaned.append(line)
                    skip_next = True
                else:
                    cleaned.append(line)

            return cleaned

        error_count = 0
        base_profile, diff_profile = qos_profile

        try:
            with open(profile_dir / f'{entity_type.value}_base.xml', 'r') as file1, \
                open(profile_dir / f'{entity_type.value}_diff.xml', 'r') as file2:

                file1_lines = file1.readlines()
                file2_lines = file2.readlines()

            # Clean both files before diffing
            file1_lines = remove_trigger_lines(file1_lines)
            file2_lines = remove_trigger_lines(file2_lines)

            # Perform diff
            diff_lines = list(
                difflib.unified_diff(
                    file1_lines,
                    file2_lines,
                    fromfile=f'{entity_type.value}_base.xml',
                    tofile=f'{entity_type.value}_diff.xml',
                    lineterm=''
                )
            )

            diff_line_count = len(diff_lines)

            # Write the result
            with open(profile_dir / f'{entity_type.value}_result.txt', 'w') as diff_file:
                diff_file.writelines(diff_lines)

            # Any difference in the profile is considered a failure
            if diff_line_count != 0:
                print_colored(logging.ERROR, "Diff Failure", f"Profile: {diff_profile.join()} - Entity: {entity_type.name}")
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
    
    def expand_qos_profile(self, qos_type: QosType, diff_path: Path, qos_profile: QosEntityData, entity_type: QosEntitiesEnum):
        def create_executable_path():
            # Windows build tree is slightly different, and binary has .exe extension
            is_windows = platform.system() == "Windows"
            path = (
                RTI_XML_UTILITY_PATH
                / "build"
                / self.connext_version.get_version(qos_type)
                / ("Release" if is_windows else "")
                / ("rtixmloutpututility.exe" if is_windows else "rtixmloutpututility")
            )
            return path

        if qos_profile == QosEntityData():
            raise BlankProfile()
        qos_profile_str, _ = qos_profile.split_entity_name()
        topic_filter = qos_profile.get_topic_filter()
        outfile = diff_path / self.create_entity_path(qos_type, entity_type)
        args = [
            str(create_executable_path()),
            '-qosFile', self.qos_files.get_file_str(qos_type),
            '-outputFile', str(outfile),
            '-qosProfile', qos_profile_str,
            '-qosTag', entity_type.value
        ]
        if topic_filter:
            args += ['-topicName', topic_filter]
        if self.delta:
            args.append('-deltaProfile')

        logger.debug(f"Running RTI XML Output Utility with args: {' '.join(args)}")

        result = subprocess.run(args, capture_output=True, text=True)
        if result.stdout:
            logger.debug(result.stdout)
        if result.stderr:
            logger.error(result.stderr)

        if not outfile.exists():
            raise FileNotFoundError
        
    @staticmethod
    def create_entity_path(qos_type: QosType, entity_type: QosEntitiesEnum) -> Path:
        return Path(f'{entity_type.value}_{qos_type.name.lower()}.xml')