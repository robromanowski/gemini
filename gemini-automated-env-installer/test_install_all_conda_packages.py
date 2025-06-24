#!/usr/bin/env python
import argparse
import subprocess
import sys
import logging
from pathlib import Path
from datetime import datetime
import csv
import json

# --- Logging Setup ---
def setup_logging(log_dir: Path):
    """Sets up file and console logging."""
    log_dir.mkdir(exist_ok=True)
    log_filename = log_dir / f"package_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log = logging.getLogger()
    if log.hasHandlers():
        log.handlers.clear()
        
    log.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    log.addHandler(console_handler)
    
    return log, log_filename

def run_conda_command(args_list: list) -> tuple[bool, str]:
    """
    Runs a conda command and captures its output.
    Returns a tuple of (success_boolean, output_string).
    """
    log = logging.getLogger()
    log.info(f"  Running command: {' '.join(args_list)}")
    try:
        # Using check=True will raise CalledProcessError on non-zero exit codes
        proc = subprocess.run(
            args_list,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return True, proc.stdout
    except FileNotFoundError:
        err_msg = f"Conda executable not found at '{args_list[0]}'"
        log.error(err_msg)
        return False, err_msg
    except subprocess.CalledProcessError as e:
        # Combine stdout and stderr for a complete error message
        err_details = f"Command failed with exit code {e.returncode}.\n"
        err_details += f"  Stderr:\n{e.stderr}\n"
        err_details += f"  Stdout:\n{e.stdout}"
        log.error(f"  {err_details}")
        return False, e.stderr.strip()
    except Exception as e:
        log.error(f"  An unexpected error occurred: {e}")
        return False, str(e)

def write_csv_report(results: list, output_path: Path):
    """Writes the test results to a CSV file."""
    if not results:
        logging.info("No results to write to CSV.")
        return
        
    fieldnames = ["package_name", "status", "details"]
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"Successfully wrote CSV report to: {output_path}")
    except Exception as e:
        logging.error(f"Failed to write CSV report. Error: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Test conda package installation from conda-forge one by one.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "package_file",
        type=Path,
        help="Path to the text file containing a list of packages to test (one per line)."
    )
    parser.add_argument(
        "-n", "--env-name",
        required=True,
        help="Name of the clean conda environment to run tests in."
    )
    parser.add_argument(
        "--conda-exe",
        default="conda",
        help="Path to the conda executable if not in PATH."
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="package_test_results",
        type=Path,
        help="Directory to store the log and CSV report."
    )
    args = parser.parse_args()

    # Setup logging and output directories
    log, log_filename = setup_logging(args.output_dir)
    log.info(f"Full log will be saved to: {log_filename}")

    # Read and clean package list
    if not args.package_file.is_file():
        log.critical(f"Package file not found: {args.package_file}")
        sys.exit(1)
        
    with open(args.package_file, 'r') as f:
        packages_to_test = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    log.info(f"Found {len(packages_to_test)} packages to test in '{args.package_file.name}'.")
    log.info(f"Using test environment: '{args.env_name}'")

    results = []
    success_count = 0
    failure_count = 0

    for i, package in enumerate(packages_to_test):
        log.info(f"--- Testing package {i+1}/{len(packages_to_test)}: {package} ---")
        
        # 1. Install the package
        install_command = [
            args.conda_exe, "install",
            "-n", args.env_name,
            "-c", "conda-forge",
            "-y", # Auto-confirm "yes"
            package
        ]
        success, details = run_conda_command(install_command)
        
        if success:
            log.info(f"  ✅ Successfully installed '{package}'.")
            results.append({"package_name": package, "status": "SUCCESS", "details": "Install successful"})
            success_count += 1
            
            # 2. Uninstall the package to clean up for the next test
            log.info(f"  Cleaning up '{package}'...")
            uninstall_command = [
                args.conda_exe, "uninstall",
                "-n", args.env_name,
                "-y",
                package
            ]
            # We run uninstall but don't need to deeply check its success for the report,
            # though the log will show an error if it fails.
            run_conda_command(uninstall_command)

        else:
            log.error(f"  ❌ Failed to install '{package}'.")
            results.append({"package_name": package, "status": "FAILURE", "details": details})
            failure_count += 1

    # --- Final Summary ---
    log.info("\n" + "="*50)
    log.info("TESTING COMPLETE")
    log.info(f"Total Packages Tested: {len(packages_to_test)}")
    log.info(f"  Success: {success_count}")
    log.info(f"  Failure: {failure_count}")
    log.info("="*50)

    # Write final report
    csv_path = args.output_dir / f"package_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    write_csv_report(results, csv_path)

    if failure_count > 0:
        log.warning("Some packages failed to install. Please review the log and CSV report for details.")

if __name__ == "__main__":
    main()
