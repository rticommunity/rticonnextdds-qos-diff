# QosDiff and QosExpand

This script will allow you to diff Qos XML files across different versions of Connext and will expand Qos profiles to account for profile inheritance and composition.

## Prerequisites

- Python 3.8+ (tested with Python 3.12)
- cmake
- git (for commit-based diffing)
- One or more RTI Connext DDS installations (version >= 6.1.0)

## Cloning

```bash
git clone --recurse-submodules https://bitbucket.org/brianr114/qos_diff.git
```

## Build QosDiff Utility
Build the submodules with the `build.py` script.  The build tool will look in the parent of `connext_dir` for other Connext installations.  The build utility expects the Connext installation folder to be named `rti_connext_dds-x.x.x`, which is the default installation name. If you use RTI scripts to setup your environment (environment variables `NDDSHOME` and `CONNEXTDDS_ARCH`), you can simply use the build script as follows:

```bash
python3 build.py
```

Otherwise, you must specify those parameters as required arguments:

```bash
usage: build.py [-h] --connext_dir CONNEXT_DIR --connext_arch CONNEXT_ARCH
```
<pre>
--connext_dir       /path/to/rti_connext_dds-x.x.x
--connext_arch      Specify your Connext DDS architecture.
</pre>

## Usage

Run the utility with the `qos_diff.py` script.

```bash
usage: qos_diff.py [-h] --qos_file QOS_FILE [--diff_file DIFF_FILE] [--commit COMMIT] [--profile PROFILE]
                   [--new_profile NEW_PROFILE] [--out_dir OUT_DIR] [--rm] [--break_on_failure] [--versions] [--expand]
```
<pre>
--qos_file          Required argument. Specify the Qos file.
--diff_file         Specify a Qos file to diff.
--commit            Specify the Git commit hash of the base file.
--profile           Specify the Qos profile as specified in the README. Otherwise all profiles will be diffed.
--new_profile       If the profile has been renamed in the diff file, specify the new Qos Profile as specified in the README.
--out_dir           Output directory for Qos files, diffs, and logs. Default is ${CWD}/output.
--rm                Delete intermediary diff output.
--break_on_failure  Break on diff failure.
--versions          Compare across different versions of Connext.
--expand            Expand the Qos profile.  Do not diff.
--delta             Only show the delta from default profile values.  Only valid with --expand.
</pre>

### Expand Qos Files

`expand` is the only additionally required flag.  Add the `delta` flag to limit the output to only show changes from the default profile.

### Diff Qos Files

Either `diff_file` or `commit` must be specified.  If both are specified, `diff_file` will be ignored.  The user will be prompted by the application to select a Connext version, and if `versions` is selected, the user will be prompted to select both the base and diff versions of Connext.

### Profile Specification

To operate on a single profile instead of the entire file, you can use the `--profile` command with arguments in the format `LIBRARY::PROFILE[::[ENTITY_NAME]::TOPIC_FILTER::ENTITY_TYPE]`.  If you choose to specify a `TOPIC_FILTER`, `ENTITY_TYPE` is required and `ENTITY_NAME` is optional.  Valid options for `ENTITY_TYPE` are: `datawriter_qos`, `datareader_qos`, `topic_qos`.

This same argument pattern is required for the `new_profile` argument.

## Common Scenarios

```bash
# Expand all profiles in QOS_FILE
python3 qos_diff.py --qos_file <QOS_FILE> --expand

# Diff all profiles in QOS_FILE against the same file in a previous Git COMMIT
python3 qos_diff.py --qos_file <QOS_FILE> --commit <COMMIT>

# Diff PROFILE in QOS_FILE against the same profile in a previous Git COMMIT
python3 qos_diff.py --qos_file <QOS_FILE> --commit <COMMIT> --profile <PROFILE>

# Diff NEW_PROFILE in QOS_FILE against PROFILE in a previous Git COMMIT
python3 qos_diff.py --qos_file <QOS_FILE> --commit <COMMIT> --profile <PROFILE> --new_profile <NEW_PROFILE>

# Diff all profiles in QOS_FILE against the a second DIFF_FILE
python3 qos_diff.py --qos_file <QOS_FILE> --diff_file <DIFF_FILE>

# Diff PROFILE in QOS_FILE against the same profile in DIFF_FILE
python3 qos_diff.py --qos_file <QOS_FILE> --diff_file <DIFF_FILE> --profile <PROFILE>

# Diff PROFILE in QOS_FILE against NEW_PROFILE in DIFF_FILE
python3 qos_diff.py --qos_file <QOS_FILE> --diff_file <DIFF_FILE> --profile <PROFILE> --new_profile <NEW_PROFILE>
```

## Troubleshooting

### Build Issues
- Ensure `NDDSHOME` and `CONNEXTDDS_ARCH` environment variables are set if using RTI scripts
- Verify cmake is installed and accessible in your PATH
- Check that your Connext installation directory follows the naming convention `rti_connext_dds-x.x.x`

### Runtime Issues
- Check the `output/log.txt` file for detailed error messages
- Ensure the QoS XML file is valid and well-formed
- Verify that specified profiles exist in the XML file

<!--
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
-->