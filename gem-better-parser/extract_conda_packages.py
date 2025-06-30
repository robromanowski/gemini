import argparse
import yaml  # Requires PyYAML: pip install PyYAML
import re
from pathlib import Path

# --- NEW: A set of common conda packages to ignore ---
# We can safely ignore these as they are fundamental to almost any
# Python environment and are guaranteed to be in conda-forge.
CONDA_IGNORE_LIST = {
    'python',
    'pip',
    'setuptools',
    'wheel',
    'certifi',
    'ca-certificates'
}


def extract_conda_packages(input_file: Path, output_file: Path):
    """
    Parses a file containing one or more concatenated conda environment.yml exports,
    extracts only the conda package names, and saves a unique, sorted list.
    """
    print(f"Reading from input file: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: Input file not found at '{input_file}'")
        return

    # A set to store unique package names automatically
    unique_conda_packages = set()

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

            for item in dependencies:
                if isinstance(item, str):
                    package_name = item.split('=')[0].strip()
                    
                    # --- MODIFIED: Check against the ignore list ---
                    if package_name and package_name not in CONDA_IGNORE_LIST:
                        unique_conda_packages.add(package_name)
                
                elif isinstance(item, dict):
                    # This intentionally does nothing for the pip section.
                    pass

        except yaml.YAMLError as e:
            print(f"  Warning: Could not parse a YAML document chunk #{doc_count}. Error: {e}")

    print(f"\nProcessed {doc_count} environment documents.")
    print(f"Found {len(unique_conda_packages)} unique, non-common conda packages.")

    # Sort the final list alphabetically and save to the output file
    sorted_packages = sorted(list(unique_conda_packages))
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for package in sorted_packages:
                f.write(f"{package}\n")
        print(f"Successfully wrote unique conda package list to: {output_file}")
    except IOError as e:
        print(f"ERROR: Could not write to output file '{output_file}'. Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract unique Conda package names from a file containing concatenated environment.yml exports, ignoring pip and common dependencies."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input text file containing one or more environment.yml exports."
    )
    parser.add_argument(
        "-o", "--output-file",
        type=Path,
        default="conda_packages_unique.txt",
        help="Path to save the final list of unique conda packages."
    )
    args = parser.parse_args()
    
    extract_conda_packages(args.input_file, args.output_file)
