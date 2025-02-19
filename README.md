# Qos Diff Script

## Cloning

```bash
git clone --recurse-submodules https://bitbucket.org/brianr114/qos_diff.git
```

## Build Qos Diff Utility
Follow directions at `<repo>/rticonnextdds-xml-output-utility/README.md` to build Qos diff utility.

## Usage

```bash
usage: qos_diff.py [-h] --qos_file QOS_FILE [--diff_file DIFF_FILE] [--commit COMMIT] [--profile PROFILE]
                   [--new_profile NEW_PROFILE] [--out_dir OUT_DIR] [--rm] [--break_on_failure]
```
<pre>
- qos_file          Required argument. Specify the Qos file.
- diff_file         Specify a Qos file to diff.
- commit            Specify the Git commit hash of the base file.
- profile           Specify the Qos profile in the format: Library::Profile. Otherwise all profiles will be diffed.
- new_profile       If the profile has been renamed in the diff file, specify the new Qos Profile in the format: Library::Profile.
- out_dir           Output directory for Qos files, diffs, and logs. Default is ${CWD}/output.
- rm                Delete intermediary diff output.
- break_on_failure  Break on diff failure.
</pre>

Either `diff_file` or `commit` must be specified.  If both are specified, `diff_file` will be ignored.

### Common Scenarios

```bash
# Diff all profiles in QOS_FILE against the same file in a previous Git COMMIT
python3 qos_diff.py --qos_file <QOS_FILE> --commit <COMMIT>

# Diff PROFILE in QOS_FILE against the same profile in a previous Git COMMIT
python3 qos_diff.py --qos_file <QOS_FILE> --commit <COMMIT> --profile <PROFILE>

# Diff NEW_PROFILE in QOS_FILE against PROFILE in a previous Git COMMIT
python3 qos_diff.py --qos_file <QOS_FILE> --commit <COMMIT> --profile <PROFILE> --new_profile <NEW_PROFILE>
```

```bash
# Diff all profiles in QOS_FILE against the a second DIFF_FILE
python3 qos_diff.py --qos_file <QOS_FILE> --diff_file <DIFF_FILE>

# Diff PROFILE in QOS_FILE against the same profile in DIFF_FILE
python3 qos_diff.py --qos_file <QOS_FILE> --diff_file <DIFF_FILE> --profile <PROFILE>

# Diff PROFILE in QOS_FILE against NEW_PROFILE in DIFF_FILE
python3 qos_diff.py --qos_file <QOS_FILE> --diff_file <DIFF_FILE> --profile <PROFILE> --new_profile <NEW_PROFILE>
```