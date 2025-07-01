# `extract_conda_packages_split_pyver.py`: Grouped Dependency Extraction Utility
 
## Goal

This script parses a text file containing one or more concatenated `environment.yml` file exports. Its purpose is to produce clean, de-duplicated lists of unique,high-level **Conda packages**, which are **grouped by the major.minor Python version** of the source environment.

This allows for more accurate, targeted validation of package availability (e.g., testing Python 3.9 packages against a Python 3.9 test environment).

## Key Features

* **Parses Concatenated Files:** Correctly handles a single input file that contains multiple `environment.yml` documents appended together.
* **Groups by Python Version:** Intelligently detects the Python version (e.g., `3.9`, `3.10`) in each environment and groups the extracted packages accordingly.
* **Excludes Pip Dependencies:** Identifies and ignores any packages listed under the `pip:` section within a dependencies list.
* **Filters Common Packages:** Automatically excludes a built-in list of foundational packages to create a focused list of user-requested libraries. The current ignorelist is:
    * `python`
    * `pip`
    * `setuptools`
    * `wheel`
    * `certifi`
    * `ca-certificates`
* **Creates Multiple, Sorted Output Files:** The script generates a separate, alphabetically sorted `.txt` file for each Python version found.

## Requirements

* Python 3.x
* The `PyYAML` library. Install it via pip:
    ```bash
    pip install PyYAML
    ```

## How to Run

```bash
python extract_conda_packages.py <input_file> [options]
```

### Input & Output Example

Given an **`input.txt`** file like this:

```yaml
name: data_science_env
dependencies:
  - python=3.9.12
  - pip
  - pandas
  - scikit-learn
name: web_app_env
dependencies:
  - python=3.10.4
  - wheel
  - requests
  - pandas
```

Running the command:
`python extract_conda_packages.py input.txt -o my_project_packages`

Will produce **two** output files:

1.  **`my_project_packages_py39.txt`**:
    ```text
    pandas
    scikit-learn
    ```
2.  **`my_project_packages_py310.txt`**:
    ```text
    pandas
    requests
    ```

### Command-Line Arguments

* **`input_file`** (Required): The path to the input text file containing the environment exports.
* **`-o, --output-prefix`** (Optional): A prefix for the output files. The script will append `_pyVERSION.txt` to this prefix for each file generated.
    * *Default:* `conda_packages`

### Example Command

```bash
# Process a file named 'all_envs.yml' and create output files like 'validation_list_py39.txt', 'validation_list_py310.txt', etc.
python extract_conda_packages.py all_envs.yml -o validation_list
```


---

# `extract_conda_packages.py`: A Conda Dependency Extraction Utility
    
## Goal

This script parses a text file containing one or more concatenated `environment.yml` file exports. Its purpose is to produce a clean, de-duplicated list of uniquehigh-level **Conda packages**. This final list is ideal for auditing package usage or for creating a manifest to validate against an internal repository like SonatypNexus.

## Key Features

* **Parses Concatenated Files:** Correctly handles a single input file that contains multiple `environment.yml` documents appended together.
* **Excludes Pip Dependencies:** Intelligently identifies and ignores any packages listed under the `pip:` section within a dependencies list.
* **Filters Common Packages:** Automatically excludes a built-in list of foundational packages that are part of almost every environment, creating a more focused lisof user-requested libraries. The current ignore list is:
    * `python`
    * `pip`
    * `setuptools`
    * `wheel`
    * `certifi`
    * `ca-certificates`
* **Creates a Unique, Sorted List:** The final output contains each package name only once and is sorted alphabetically.

## Requirements

* Python 3.x
* The `PyYAML` library. Install it via pip:
    ```bash
    pip install PyYAML
    ```

## How to Run

```bash
python extract_conda_packages.py <input_file> [options]
```

### Input File Format

The script expects a single text file containing the content of one or more `environment.yml` files.

*Example `input.txt`:*

```yaml
name: data_science_env
channels:
  - conda-forge
dependencies:
  - python=3.9
  - pip
  - pandas
  - scikit-learn
  - pip:
    - some-pip-package==1.2.3
name: web_app_env
channels:
  - conda-forge
dependencies:
  - python=3.10
  - wheel
  - requests
  - pandas
```

### Command-Line Arguments

* **`input_file`** (Required): The path to the input text file containing the environment exports.
* **`-o, --output-file`** (Optional): The name of the file to save the final list of unique Conda packages.
    * *Default:* `conda_packages_unique.txt`

### Output

The script generates a simple text file with one package name per line.

*Example output from the input above:*

```text
pandas
requests
scikit-learn
```

### Example Command

```bash
# Process a file named 'all_environment_exports.txt' and save the clean list to 'packages_to_test.txt'
python extract_conda_packages.py all_environment_exports.txt -o packages_to_test.txt
```
