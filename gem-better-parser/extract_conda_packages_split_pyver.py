import argparse
import yaml  # Requires PyYAML: pip install PyYAML
import re
from pathlib import Path
from collections import defaultdict

# A set of common conda packages to ignore
CONDA_IGNORE_LIST = {
    'python',
    'pip',
    'setuptools',
    'wheel',
    'certifi',
    'ca-certificates'
}

def find_python_version(dependencies: list) -> str | None:
    """Scans dependency list and extracts the major.minor python version."""
    if not dependencies:
        return None
    # Regex to find 'python' and capture the major.minor version (e.g., 3.9, 3.10)
    py_ver_re = re.compile(r"^python\s*=\s*(\d+\.\d+)")
    for item in dependencies:
        if isinstance(item, str):
            match = py_ver_re.match(item)
            if match:
                return match.group(1) # e.g., "3.9"
    return None

def extract_conda_packages(input_file: Path, output_prefix: str):
    """
    Parses a file containing conda environment exports, groups packages by Python
    version, and saves a unique, sorted list for each version.
    """
    print(f"Reading from input file: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: Input file not found at '{input_file}'")
        return

    # A dictionary to hold sets of packages, keyed by Python version
    # e.g., {"3.9": {"pandas", "numpy"}, "3.10": {"requests"}}
    packages_by_python = defaultdict(set)

    # Split the content by 'name:' which typically starts a new YAML document
    env_yaml_chunks = filter(None, re.split(r'\n(?=name:)', content))

    doc_count = 0
    for chunk in env_yaml_chunks:
        doc_count += 1
        try:
            data = yaml.safe_load(chunk)
            
            if not isinstance(data, dict):
                print(f"  Skipping document #{doc_count} as it's not a valid environment structure.")
                continue

            dependencies = data.get('dependencies', [])
            if not dependencies or not isinstance(dependencies, list):
                continue
            
            # --- NEW LOGIC: First, find the Python version for this env ---
            py_version = find_python_version(dependencies)
            if not py_version:
                print(f"  Warning: No Python version found in document #{doc_count}. Skipping.")
                continue

            # --- Now, collect packages for this specific Python version ---
            for item in dependencies:
                if isinstance(item, str):
                    package_name = item.split('=')[0].strip()
                    if package_name and package_name not in CONDA_IGNORE_LIST:
                        packages_by_python[py_version].add(package_name)

        except yaml.YAMLError as e:
            print(f"  Warning: Could not parse a YAML document chunk #{doc_count}. Error: {e}")

    print(f"\nProcessed {doc_count} environment documents.")
    print(f"Found packages for {len(packages_by_python)} Python versions: {', '.join(sorted(packages_by_python.keys()))}")

    # --- NEW LOGIC: Write a separate file for each Python version ---
    output_dir = Path(output_prefix).parent
    output_dir.mkdir(parents=True, exist_ok=True) # Ensure output directory exists

    for py_ver, package_set in packages_by_python.items():
        # Sanitize version string for filename (e.g., "3.9" -> "py39")
        filename_suffix = f"_py{py_ver.replace('.', '')}.txt"
        output_filename = Path(output_prefix).name + filename_suffix
        output_path = output_dir / output_filename
        
        sorted_packages = sorted(list(package_set))
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for package in sorted_packages:
                    f.write(f"{package}\n")
            print(f"  -> Successfully wrote {len(sorted_packages)} packages to: {output_path}")
        except IOError as e:
            print(f"  -> ERROR: Could not write to output file '{output_path}'. Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract unique Conda package names from concatenated environment files, grouped by Python version."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input text file containing one or more environment.yml exports."
    )
    parser.add_argument(
        "-o", "--output-prefix",
        default="conda_packages",
        help="A prefix for the output files. The script will append '_pyVERSION.txt' to this prefix."
    )
    args = parser.parse_args()
    
    extract_conda_packages(args.input_file, args.output_prefix)
