# Batch Conda Environment Migration YAML Generator (`batch_generate_yamls_conditional_archive.py`)

## Purpose

This script automates the process of generating Conda environment YAML files suitable for migrating existing environments to use the `conda-forge` channel. It is designed specifically for scenarios where you need to process numerous environments across multiple users (e.g., on a shared server) and where the standard `conda env export --from-history` command may produce unreliable or undesirable output (like including build strings or full dependency lists) for older or non-standard environments.

The script aims to create the "cleanest" possible automated definition by:
1.  Discovering all conda environments within specified directories.
2.  Attempting to use the environment's history (`--from-history`) if it appears clean and minimal (checks for build strings and excessive length).
3.  Falling back to using a heuristically filtered version of `conda list --export` if the history seems unreliable.
4.  Preserving the original Python version found in the environment.
5.  Explicitly setting `conda-forge` as the primary channel in the output YAML.
6.  Archiving the raw outputs from the `conda` commands used for each environment for later review or debugging.

**NOTE:** This script generates environment *definition files*. It does **not** create the actual environments itself. The generated YAML files must be reviewed and then used with `conda env create -f <filename.yml>`. Thorough testing of the created environments is crucial.

## Features

* **Batch Processing:** Discovers and processes multiple conda environments recursively within specified paths.
* **Conditional Logic:** Automatically detects likely unreliable `--from-history` output (based on dependency count and presence of build strings) and switches to a fallback method.
* **History-Based Method (Preferred):** When history is reliable, uses `conda env export --from-history --no-builds` to generate a minimal YAML containing explicitly installed packages.
* **Fallback Method (Filtered Export):** When history is unreliable, uses `conda list --export`, parses the `package=version` list, and applies a heuristic filter to remove common low-level dependencies.
* **Preserves Python Version:** Identifies and keeps the original Python version specifier from the source environment in the final YAML.
* **Targets Conda-Forge:** Explicitly sets `channels: [- conda-forge]` in all generated YAML files.
* **Cleans Pip Dependencies:** Extracts pip dependencies (using `conda env export --no-builds`) and removes version specifiers. Note: The fallback method (`conda list --export`) does not capture pip packages itself, but the script still tries to get them via the separate `--no-builds` export.
* **Archives Raw Data:** Saves the raw output from `conda env export --from-history --no-builds` and (if used) `conda list --export` into separate subdirectories for reference.
* **Configurable:** Search paths, output directory, conda executable path, filtering list, `shell=True` usage, and verbosity can be controlled via command-line arguments or internal script variables.

## Prerequisites

* Python 3.x
* `PyYAML` library: Install via `pip install PyYAML`
* `packaging` library: Install via `pip install packaging`
* A working `conda` executable accessible by the script.

## Configuration (Inside the Script)

While most options are command-line arguments, you might want to review/customize these variables near the top of the script file:

* **`FILTER_OUT_PACKAGES` (Set):** This set contains package names that will be *removed* when the script uses the fallback (`conda list --export`) method. Review and **customize this list** based on common dependencies you *don't* want in your final YAMLs. Be careful not to remove something essential!
* **`HISTORY_LENGTH_THRESHOLD` (Integer):** The number of dependencies found in `--from-history` output above which the script considers the history "bad" and uses the fallback method. Default is 50, adjust if needed.
* **`BUILD_STRING_RE` (Regex):** The pattern used to detect build strings in history output. Generally should not need changing.

## Usage

Run the script from your terminal. Provide the paths to search and potentially other arguments. If searching other users' directories, you will likely need to run the script using `sudo`.

**Command Structure:**

```bash
sudo /path/to/your/python batch_generate_yamls_conditional_archive.py \
    [SEARCH_PATH_1] [SEARCH_PATH_2] ... \
    --conda-exe /path/to/target/conda \
    [-o OUTPUT_DIRECTORY] \
    [--use-shell] \
    [-v]
```

**Arguments:**

* **`search_paths`** (Required, Positional): One or more directory paths to search recursively for conda environments. Remember to use the path format (with/without trailing slash) that worked correctly with `find` on your system during testing (e.g., `/export/home/` or `/export/home`).
* **`-o OUTPUT_DIRECTORY`, `--output-dir OUTPUT_DIRECTORY`** (Optional): The main directory where the final YAML files and archive subdirectories will be created. Defaults to `conda_forge_yamls_conditional`.
* **`--conda-exe CONDA_EXE`** (Optional but Recommended, esp. with `sudo`): The full path to the `conda` executable the script should use. Defaults to `conda` (relies on finding it in `PATH`). **Crucially important when running with `sudo`** to specify the correct conda path, as `sudo` often uses a minimal `PATH`.
* **`--use-shell`** (Optional Flag): If present, runs the internal `conda` commands using `shell=True` in `subprocess.run`. **Use with caution!** Only needed if direct execution fails with `Permission denied (errno 13)` errors, as discovered during previous debugging steps. Carries potential security risks if command arguments could be manipulated.
* **`-v`, `--verbose`** (Optional Flag): Enables detailed DEBUG level logging output, showing more steps and filtering decisions.

**Example:**

```bash
sudo /usr/bin/python3 batch_generate_yamls_conditional_archive.py \
    /export/home/ /opt/envs \
    --conda-exe /opt/miniforge3/bin/conda \
    -o /scratch/conda_migration_yamls \
    -v
```
## Workflow

1. Configure: Adjust `FILTER_OUT_PACKAGES` inside the script if needed.
2. Run Script: Execute the script with appropriate search paths and options (using `sudo` if scanning other users' directories and `--conda-exe` to point to the correct conda binary).
3. Review Output Directory: After the script runs, check the specified output directory (e.g., `conda_forge_yamls_conditional` (default) or the one specified with `-o`). You will find:
* `.yml` files: The final generated environment definitions, named after the original environment path (e.g., `export_home_user_env_name.yml`). Filenames are prefixed `cf_hist_` or `cf_filt_` depending on the method used.
* `raw_history_outputs/` subdir: Contains `.yml` files holding the raw output of `conda env export --from-history --no-builds` for each environment.
* `raw_list_export_outputs/` subdir: Contains `.txt` files holding the raw output of `conda list --export` for environments where the script used the fallback method.
4. Review Generated YAMLs: Examine the `.yml` files in the main output directory. Do they look reasonable? Does the dependency list seem appropriate? Was the correct Python version preserved?
5. Create New Environments: Choose a generated YAML file and create the environment using a `conda-forge` aware `conda` installation:
```bash
# Make sure you are using conda from Miniforge or similar
conda env create -f /path/to/output/dir/some_env_name.yml
```
6.TEST! TEST! TEST!: Activate the newly created environment (`conda activate <env_name_from_yaml>`) and thoroughly test the original application, code, or workflow that used it. This is the most critical step to ensure the migration was successful and functional.
7. Iterate: If testing fails, examine the generated YAML, the raw outputs, and potentially adjust the `FILTER_OUT_PACKAGES` list or manually edit the generated YAML for that specific environment before attempting to recreate it.

## Output Structure
If you run the script with `-o my_conda_output`, the structure will be:
```
my_conda_output/
├── cf_filt_export_home_user1_envs_bad_hist.yml   # Final YAML (fallback method used)
├── cf_hist_export_home_user2_envs_good_hist.yml  # Final YAML (history method used)
├── ... (other final YAMLs) ...
│
├── raw_history_outputs/
│   ├── export_home_user1_envs_bad_hist_history.yml  # Raw history output
│   ├── export_home_user2_envs_good_hist_history.yml # Raw history output
│   └── ... (other raw history files) ...
│
└── raw_list_export_outputs/
    ├── export_home_user1_envs_bad_hist_list_export.txt # Raw list export (only if fallback used)
    └── ... (other raw list export files) ...
```

## Limitations and Caveats
* Heuristic Filtering: The fallback method relies on filtering common dependency names. This is *not* guaranteed to be accurate and may remove needed packages or leave unnecessary ones. Customize `FILTER_OUT_PACKAGES`.
* History Check Heuristic: The check for "good" vs "bad" history output is also a heuristic (based on length and build strings) and might misclassify some environments.
* Build Strings: The script aims to produce YAMLs without build strings, primarily by using `--no-builds` or parsing `conda list --export`.
* Pip Packages: The fallback method (`conda list --export`) does not capture pip-installed packages. The history method relies on a separate `conda env export --no-builds` call to find pip packages and then strips their versions. A separate `pip freeze` execution would be needed for full pip capture including versions.
* Testing is Essential: Creating the environment successfully does not guarantee functional equivalence. Minor version changes from `conda-forge` or missing/filtered dependencies can break workflows. Testing is mandatory.
* `shell=True`: Use the `--use-shell` flag only if required to overcome `Permission denied` errors during `conda` execution via `subprocess`, and be aware of the security implications.




