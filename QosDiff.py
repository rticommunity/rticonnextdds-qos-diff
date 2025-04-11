import os
from enum import Enum
from  utils import *

class QosType(Enum):
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
        self.base = QosDiffFile(args.out_dir, QosType.BASE)
        self.diff = QosDiffFile(args.out_dir, QosType.DIFF)
        self.perform_diff = not args.expand
        self.rm = args.rm
        self.break_on_failure = args.break_on_failure

        # Define the Profiles
        self.qos_profiles = set()

    def get_profiles(self, profile, new_profile):
        if profile == '':
            self.qos_profiles.update(find_qos_profiles(self.base.path))
            self.qos_profiles.update(find_qos_profiles(self.diff.path))
        elif new_profile != '':
            self.qos_profiles.add((profile, new_profile))
        else:
            self.qos_profiles.add((profile, profile))