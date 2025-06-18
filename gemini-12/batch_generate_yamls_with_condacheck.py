import argparse
import subprocess
import yaml # PyYAML library (pip install PyYAML)
import re
import os
import sys
import logging
from pathlib import Path
from functools import partial
import shutil # For shutil.which
from datetime import datetime
import csv

# --- Logging Setup ---
log = logging.getLogger()
if log.hasHandlers(): log.handlers.clear()
log.setLevel(logging.INFO)
log_filename = f"batch_generate_yamls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_filename)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log.addHandler(file_handler)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
log.addHandler(console_handler)

# --- Filtering Configuration ---
FILTER_OUT_PACKAGES = {
    "_libgcc_mutex", "_openmp_mutex", "bzip2", "ca-certificates",
    "ld_impl_linux-64", "libffi", "libgcc-ng", "libgomp", "libstdcxx-ng",
    "libuuid", "ncurses", "openssl", "readline", "sqlite", "tk", "tzdata",
    "xz", "zlib", "certifi", "setuptools", "pip", "wheel", "six", "zipp",
}
HISTORY_LENGTH_THRESHOLD = 50
BUILD_STRING_RE = re.compile(r"=\w*h[0-9a-f]{7,}|=\w+_\d+$|=main$")

# --- Helper Functions ---
winOS = sys.platform == "win32"
def path2str0(p: Path, win_os: bool = True): s = str(p) if win_os else p.as_posix(); return s
path2str = partial(path2str0, win_os=winOS)

def run_conda_command(conda_exe_path: str, args_list: list, env_path: Path = None, use_shell: bool = False):
    command = [str(conda_exe_path)] + args_list
    if env_path and '--version' not in args_list:
        command.extend(['-p', path2str(env_path)])
    
    cmd_str_for_log = " ".join(command)
    cmd_exec = cmd_str_for_log if use_shell else command
    log.info(f"  Running: {cmd_str_for_log}")
    try:
        proc = subprocess.run(cmd_exec, capture_output=True, text=True, check=True, shell=use_shell, timeout=180)
        return proc.stdout
    except subprocess.CalledProcessError as e: log.error(f"  ERROR running command: {cmd_str_for_log}\n  Stderr: {e.stderr}"); raise
    except FileNotFoundError: log.error(f"  ERROR: Conda executable not found at '{conda_exe_path}'."); raise
    except subprocess.TimeoutExpired: log.error(f"  ERROR: Command timed out: {cmd_str_for_log}"); raise
    except Exception as e: log.error(f"  ERROR running command: {cmd_str_for_log}\n  Exception: {e}"); raise

def get_pip_deps_from_export(export_yaml_data: dict) -> dict | None:
    pip_deps_section = None
    if not isinstance(export_yaml_data, dict): return None
    dependencies = export_yaml_data.get("dependencies", [])
    if not isinstance(dependencies, list): return None
    for item in dependencies:
        if isinstance(item, dict) and "pip" in item: pip_deps_section = item; break
    if pip_deps_section is None or 'pip' not in pip_deps_section or not isinstance(pip_deps_section['pip'], list): return None
    regex_ver = r"(==|>=|<=|<|>|~=)\s*[\w\.\-\+]+.*"; regex_build = r"\s*#.*"
    cleaned_list = []
    for p in pip_deps_section["pip"]:
        if isinstance(p, str):
            p_no_build = re.sub(regex_build, "", p).strip(); p_cleaned = re.sub(regex_ver, "", p_no_build).strip()
            if p_cleaned: cleaned_list.append(p_cleaned)
        else: log.warning(f"  Skipping non-string pip dependency: {p}")
    if not cleaned_list: return None
    return {'pip': cleaned_list}

def parse_conda_list_export(export_output: str) -> list:
    dependencies = []
    lines = export_output.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'): continue
        parts = line.split('=')
        if len(parts) >= 2:
            package_name = '='.join(parts[:-2]) if len(parts) > 2 else parts[0]; version = parts[-2]
            dependencies.append(f"{package_name}={version}")
        elif len(parts) == 1: dependencies.append(parts[0])
    return dependencies

def is_history_output_good(hist_data: dict) -> tuple[bool, str]:
    if not hist_data or 'dependencies' not in hist_data or not isinstance(hist_data['dependencies'], list):
        return False, "Invalid history format"
    dependencies = hist_data['dependencies']
    if len(dependencies) > HISTORY_LENGTH_THRESHOLD:
        return False, f"Dependency count ({len(dependencies)}) > threshold ({HISTORY_LENGTH_THRESHOLD})"
    for dep in dependencies:
        if not isinstance(dep, str): continue
        if BUILD_STRING_RE.search(dep): return False, f"Found build string in '{dep}'"
        package_name = dep.split('=')[0].strip()
        if package_name in FILTER_OUT_PACKAGES: return False, f"Found low-level package '{package_name}'"
    return True, "Clean"

def save_raw_output(output_dir: Path, filename: str, content: str):
    try:
        output_filepath = output_dir / filename; output_filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filepath, 'w') as f: f.write(content)
        log.info(f"  Saved raw output: {output_filepath}")
    except Exception as e: log.error(f"  ERROR saving raw output {output_filepath}. Error: {e}")

def get_latest_mtime_in_dir(dir_path: Path) -> datetime | None:
    latest_mtime = 0
    try:
        for root, _, files in os.walk(dir_path):
            for file in files:
                try:
                    filepath = Path(root) / file; mtime = filepath.stat().st_mtime
                    if mtime > latest_mtime: latest_mtime = mtime
                except (FileNotFoundError, PermissionError): continue
    except Exception as e:
        log.debug(f"Could not scan directory {dir_path} for mtime: {e}"); return None
    return datetime.fromtimestamp(latest_mtime) if latest_mtime > 0 else None

def get_creation_conda_version(history_file_path: Path) -> str:
    """Parses the conda-meta/history file to find the first conda version listed."""
    if not history_file_path.is_file():
        return "Unknown"
    try:
        with open(history_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith("# conda version:"):
                    return line.split(':')[1].strip()
    except Exception as e:
        log.debug(f"Could not read or parse history file {history_file_path}: {e}")
    return "Unknown"

def find_conda_environments(search_paths: list) -> list[tuple[Path, datetime | None, str]]:
    """Finds envs and returns their path, last modified date, and creation conda version."""
    env_data = []
    for base_path_str in search_paths:
        base_path = Path(base_path_str).resolve(); log.info(f"Searching for environments under: {base_path}")
        if not base_path.is_dir(): log.warning(f"  Search path '{base_path_str}' not found or not a directory. Skipping."); continue
        for root, dirs, files in os.walk(base_path, topdown=True, onerror=lambda err: log.error(f"  Permission error accessing {err.filename} - Skipping subtree.")):
            if 'conda-meta' in dirs:
                env_path = Path(root)
                history_file = env_path / 'conda-meta' / 'history'
                if history_file.exists() and not (env_path / 'pkgs').is_dir():
                    log.info(f"  Found potential env: {env_path}")
                    last_modified = get_latest_mtime_in_dir(env_path)
                    creation_conda_ver = get_creation_conda_version(history_file)
                    env_data.append((env_path, last_modified, creation_conda_ver))
                    dirs[:] = []
                else:
                    log.debug(f"  Skipping {env_path}, doesn't look like a standard named/prefix env or history missing."); dirs[:] = []
            dirs[:] = [d for d in dirs if d not in ['.git', '.svn', 'node_modules', '__pycache__', 'pkgs', 'pkgs_dirs', '.cache']]
    return env_data

def process_environment(env_path: Path, output_dir_hist: Path, output_dir_fall: Path, archive_hist_dir: Path, archive_list_dir: Path, conda_exe: str, use_shell: bool, use_original_name: bool) -> dict:
    log.info(f"Processing environment: {env_path}")
    original_env_name = env_path.name
    result = {
        "env_name": original_env_name, "env_path": str(env_path), "current_conda_version": "N/A", "method": "N/A",
        "status": "ERROR", "kept": 0, "filtered": 0, "filtered_list": "", "notes": ""
    }
    safe_filename_base = path2str(env_path).replace(os.path.sep, '_').strip('_')
    
    try:
        conda_in_env_path = env_path.parent.parent / "bin" / "conda"
        if conda_in_env_path.exists(): version_output = run_conda_command(str(conda_in_env_path), ['--version'], use_shell=use_shell)
        else: version_output = run_conda_command(conda_exe, ['--version'], use_shell=use_shell)
        match = re.search(r'conda\s+([\d\.]+)', version_output)
        if match: result['current_conda_version'] = match.group(1); log.info(f"  Found Current Conda Version: {result['current_conda_version']}")
    except Exception as e:
        log.warning(f"  Could not determine current conda version. Error: {e}"); result['current_conda_version'] = "Unknown"
    
    try:
        history_output = run_conda_command(conda_exe, ['env', 'export', '--from-history', '--no-builds'], env_path, use_shell)
        save_raw_output(archive_hist_dir, f"{safe_filename_base}_history.yml", history_output); hist_data = yaml.safe_load(history_output)
    except Exception as e:
        log.error(f"  ERROR getting or parsing history. Error: {e}"); result['notes'] = f"Failed to get/parse history: {e}"; return result

    pip_section = None; notes_list = []
    try:
        nobuild_output = run_conda_command(conda_exe, ['env', 'export', '--no-builds'], env_path, use_shell)
        nobuild_data = yaml.safe_load(nobuild_output); pip_section = get_pip_deps_from_export(nobuild_data)
    except Exception as e:
        log.warning(f"  WARNING: Failed to get/process pip deps. Error: {e}"); notes_list.append("Pip processing failed")

    history_is_good, reason = is_history_output_good(hist_data)
    final_yaml_data = None

    if history_is_good:
        result['method'] = "History"
        log.info(f"  Processing using good {result['method']} data.")
        try:
            original_python_spec = None
            dependencies_from_hist = hist_data.get('dependencies', [])
            for dep in dependencies_from_hist:
                if isinstance(dep, str) and (dep == 'python' or re.match(r"^python\s*(=|<|>|>=|<=|~=)", dep)):
                    original_python_spec = dep; break
            if not original_python_spec: log.warning(f"  Could not find Python in apparently good history for {env_path}.")
            new_deps = []
            if original_python_spec: new_deps.append(original_python_spec)
            hist_dep_names = {d.split('=<>')[0].strip() for d in dependencies_from_hist if isinstance(d, str)}
            if "pip" not in hist_dep_names: new_deps.append("pip")
            if "setuptools" not in hist_dep_names: new_deps.append("setuptools")
            if "wheel" not in hist_dep_names: new_deps.append("wheel")
            for dep in dependencies_from_hist:
                if isinstance(dep, str):
                    dep_name = dep.split('=<>')[0].strip()
                    if dep_name in ['python', 'pip', 'setuptools', 'wheel']: continue
                    new_deps.append(dep)
                elif isinstance(dep, dict) and 'pip' in dep: continue
                else: log.warning(f"  Keeping unexpected complex entry from good history: {dep}"); new_deps.append(dep)
            if pip_section: new_deps.append(pip_section)
            final_env_name = original_env_name if use_original_name else f"cf_hist_{original_env_name}"
            final_yaml_data = {'name': final_env_name, 'channels': ['conda-forge'], 'dependencies': new_deps}
        except Exception as e:
            err_msg = f"ERROR processing good history: {e}"; log.error(f"  {err_msg}"); notes_list.append(err_msg)
    else:
        result['method'] = "Fallback"
        log.info(f"  Falling back to filtered 'conda list --export' method. Reason: {reason}")
        try:
            list_export_output = run_conda_command(conda_exe, ['list', '--export'], env_path, use_shell)
            save_raw_output(archive_list_dir, f"{safe_filename_base}_list_export.txt", list_export_output)
            dependencies_from_list = parse_conda_list_export(list_export_output)
            if not dependencies_from_list: raise ValueError("Parsed dependency list is empty.")
            original_python_spec = None
            for dep in dependencies_from_list:
                if dep.startswith('python='): original_python_spec = dep; break
            if not original_python_spec: log.warning(f"  Could not find Python in list --export for {env_path}.")
            new_deps = []; kept_count, filtered_count = 0, 0; filtered_packages_list = []
            if original_python_spec: new_deps.append(original_python_spec)
            new_deps.extend(["pip", "setuptools", "wheel"])
            for dep in dependencies_from_list:
                package_name = dep.split('=')[0].strip()
                if package_name in ['python', 'pip', 'setuptools', 'wheel']: continue
                if package_name in FILTER_OUT_PACKAGES: filtered_count += 1; filtered_packages_list.append(dep)
                else: new_deps.append(dep); kept_count += 1
            if filtered_packages_list: log.info(f"  Filtered out {filtered_count} common dependencies: {', '.join(filtered_packages_list)}")
            log.info(f"  Summary: Kept {kept_count} packages after filtering.")
            result.update({'kept': kept_count, 'filtered': filtered_count, 'filtered_list': ", ".join(filtered_packages_list)})
            if kept_count == 0: notes_list.append("Kept 0 packages")
            if pip_section: new_deps.append(pip_section)
            final_env_name = original_env_name if use_original_name else f"cf_filt_{original_env_name}"
            final_yaml_data = {'name': final_env_name, 'channels': ['conda-forge'], 'dependencies': new_deps}
        except Exception as e:
            err_msg = f"ERROR processing with fallback: {e}"; log.error(f"  {err_msg}"); notes_list.append(err_msg)

    if final_yaml_data:
        output_dir = output_dir_hist if history_is_good else output_dir_fall
        output_filepath = output_dir / f"{safe_filename_base}.yml"
        try:
            with open(output_filepath, 'w') as f: yaml.dump(final_yaml_data, f, default_flow_style=False, sort_keys=False)
            log.info(f"  Successfully generated final ({result['method']} method): {output_filepath}")
            result['status'] = "OK"
        except Exception as e:
            err_msg = f"ERROR writing final YAML: {e}"; log.error(f"  {err_msg}"); notes_list.append(err_msg)
    
    result['notes'] = "; ".join(notes_list)
    return result

def write_summary_csv(results: list, output_filepath: Path):
    if not results: log.info("No results to write to CSV."); return
    fieldnames = [
        "env_name", "env_path", "last_modified", "creation_conda_version", "current_conda_version",
        "status", "method", "kept", "filtered", "notes", "filtered_list"
    ]
    log.info(f"Writing summary to CSV file: {output_filepath}")
    try:
        with open(output_filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        log.info("Successfully wrote CSV summary.")
    except Exception as e: log.error(f"Failed to write CSV summary. Error: {e}")

# --- Main Execution Logic ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch generate conda environment YAMLs...", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("search_paths", nargs='+', help="Base paths to search for conda environments.")
    parser.add_argument("-o", "--output-dir", default="conda_forge_yamls_conditional", help="Main directory for final YAMLs and raw archives.")
    parser.add_argument("--conda-exe", default="conda", help="Path to conda executable.")
    parser.add_argument("--use-shell", action='store_true', help="Use shell=True for conda commands (USE WITH CAUTION!).")
    parser.add_argument("-v", "--verbose", action='store_const', dest='log_level', const=logging.DEBUG, default=logging.INFO, help="Enable verbose (DEBUG) logging.")
    parser.add_argument("--use-original-name", action='store_true', help="Use the original environment name in the output YAML.")
    args = parser.parse_args()
    log.setLevel(args.log_level)
    log.info(f"All output is being logged to: {log_filename}")

    output_dir_main = Path(args.output_dir).resolve(); output_dir_history_ok = output_dir_main / "from_history"; output_dir_fallback = output_dir_main / "from_fallback"; archive_dir_history = output_dir_main / "raw_history_outputs"; archive_dir_list = output_dir_main / "raw_list_export_outputs"
    try:
        output_dir_main.mkdir(parents=True, exist_ok=True); output_dir_history_ok.mkdir(parents=True, exist_ok=True); output_dir_fallback.mkdir(parents=True, exist_ok=True); archive_dir_history.mkdir(parents=True, exist_ok=True); archive_dir_list.mkdir(parents=True, exist_ok=True)
        log.info(f"Main output directory: {output_dir_main}"); log.info(f"  - Clean history YAMLs will be saved in: {output_dir_history_ok}"); log.info(f"  - Fallback method YAMLs will be saved in: {output_dir_fallback}"); log.info(f"Raw history archive: {archive_dir_history}"); log.info(f"Raw list export archive: {archive_dir_list}")
    except Exception as e: log.critical(f"Failed to create output directories under '{output_dir_main}'. Error: {e}"); sys.exit(1)
    
    conda_exe_path = Path(args.conda_exe); resolved_path = shutil.which(args.conda_exe)
    if not conda_exe_path.is_file() and '/' not in args.conda_exe and '\\' not in args.conda_exe:
        if resolved_path: conda_exe_path = Path(resolved_path); log.info(f"Found conda executable via PATH: {conda_exe_path}")
        else: log.critical(f"Conda executable '{args.conda_exe}' not found."); sys.exit(1)
    elif not conda_exe_path.is_file(): log.critical(f"Specified conda executable path not found: {conda_exe_path}"); sys.exit(1)
    else: log.info(f"Using specified conda executable: {conda_exe_path}")
    
    log.info("Starting environment discovery...")
    search_paths_str = [str(p) for p in args.search_paths]
    found_envs_data = find_conda_environments(search_paths_str)
    log.info(f"Discovery finished. Found {len(found_envs_data)} potential environments.")

    if found_envs_data:
        log.info("Starting environment processing...")
        all_results = []
        found_envs_data.sort(key=lambda x: x[1] if x[1] else datetime.max)

        for env_path, last_modified, creation_conda_ver in found_envs_data:
            try:
                result_dict = process_environment(
                    env_path, output_dir_history_ok, output_dir_fallback,
                    archive_dir_history, archive_list_dir,
                    str(conda_exe_path), args.use_shell, args.use_original_name
                )
                result_dict['last_modified'] = last_modified.strftime('%Y-%m-%d') if last_modified else "Unknown"
                result_dict['creation_conda_version'] = creation_conda_ver
                all_results.append(result_dict)
            except Exception as e:
                log.error(f"CRITICAL ERROR processing {env_path}. Error: {e}")
                all_results.append({
                    "env_name": env_path.name, "env_path": str(env_path), 
                    "last_modified": last_modified.strftime('%Y-%m-%d') if last_modified else "Unknown",
                    "creation_conda_version": creation_conda_ver,
                    "current_conda_version": "N/A", "status": "CRITICAL ERROR", "method": "N/A", 
                    "kept": 0, "filtered": 0, "filtered_list": "", "notes": str(e)
                })
        
        csv_path = output_dir_main / f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        write_summary_csv(all_results, csv_path)

        log.info("\n\n" + "="*80); log.info("FINAL PROCESSING SUMMARY"); log.info("="*80)
        total_envs = len(all_results); ok_count = sum(1 for r in all_results if r['status'] == "OK"); fallback_count = sum(1 for r in all_results if r['method'] == "Fallback"); history_ok_count = ok_count - fallback_count; error_count = total_envs - ok_count
        log.info(f"Total Environments Processed: {total_envs}"); log.info(f"  Successfully Generated: {ok_count}"); log.info(f"  Errors / Not Generated: {error_count}"); log.info(f"  --- Breakdown of Successes ---"); log.info(f"    Processed via Clean History: {history_ok_count}"); log.info(f"    Processed via Fallback Method: {fallback_count}"); log.info(f"  Summary CSV created at: {csv_path}"); log.info("-"*80)
        
        log.info("Breakdown by Environment (Oldest first):")
        for r in all_results:
            notes_str = f" | Notes: {r['notes']}" if r['notes'] else ""
            status_str = f"Status: {r['status']} ({r['method']})"
            log.info(f"  - Env: {r['env_path']}")
            log.info(f"    - Last Mod: {r['last_modified']:<11} | Created With: {r['creation_conda_version']:<10} | Managed By: {r['current_conda_version']:<10} | {status_str}{notes_str}")
        
        if error_count > 0:
            log.info("\n--- Environments with Errors ---")
            for r in all_results:
                if r['status'] != "OK":
                    log.info(f"  - Env: {r['env_path']} | Status: {r['status']} | Details: {r['notes']}")
        log.info("="*80)
    else:
        log.info("No environments found to process.")

    log.info(f"Script finished. Full log available in: {log_filename}")
