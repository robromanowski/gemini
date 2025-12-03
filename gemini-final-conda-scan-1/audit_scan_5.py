import os
import json
import subprocess
import csv
import socket
import sys

# --- CONFIGURATION ---

# !!! IMPORTANT: PUT THE FULL PATH TO CONDA HERE !!!
CONDA_EXE = "/opt/anaconda3/bin/conda" 

INTERNAL_NEXUS_URL = "nexus.yourdomain.com" 

ALLOWED_INDICATORS = ["conda-forge", INTERNAL_NEXUS_URL]
ANACONDA_INDICATORS = ["repo.anaconda.com", "pkgs/main", "pkgs/r", "pkgs/msys2", "defaults"]

SCAN_ROOTS = ["/home", "/opt", "/usr/local"]

HOSTNAME = socket.gethostname()
REPORT_FILE = f"conda_audit_detailed_{HOSTNAME}.csv"
SUMMARY_FILE = f"conda_audit_dirty_envs_{HOSTNAME}.txt"

# ---------------------

def get_conda_packages(env_path):
    try:
        result = subprocess.run(
            [CONDA_EXE, "list", "-p", env_path, "--json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # We don't print stderr here anymore to keep the output clean
            # We will count it as a "Scan Error"
            return "ERROR"
            
        return json.loads(result.stdout)
    except FileNotFoundError:
        print(f"    ! CRITICAL: The script cannot find the conda executable at {CONDA_EXE}")
        sys.exit(1)
    except Exception as e:
        return "ERROR"

def analyze_package(pkg):
    name = pkg.get('name', 'unknown')
    channel = pkg.get('channel')

    if not channel:
        return "RISK_EMPTY_CHANNEL"

    if any(bad in channel for bad in ANACONDA_INDICATORS):
        return "VIOLATION_ANACONDA_DEFAULT"

    is_allowed = False
    for allowed in ALLOWED_INDICATORS:
        if allowed in channel:
            is_allowed = True
            break
    
    if not is_allowed:
        if channel == "pypi":
             return "PASS" 
        return f"RISK_UNKNOWN_CHANNEL_({channel})"

    return "PASS"

def scan_filesystem():
    discovered_envs = []
    print(f"[*] Scanning filesystem for 'conda-meta' in: {SCAN_ROOTS}...")
    
    for root_dir in SCAN_ROOTS:
        if not os.path.exists(root_dir):
            continue
            
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if "conda-meta" in dirnames:
                env_path = dirpath
                discovered_envs.append(env_path)
                dirnames.remove("conda-meta") 
                
    return discovered_envs

def main():
    if os.geteuid() != 0:
        print("[-] WARNING: Not running as root. You will miss user environments.")
    
    if not os.path.isfile(CONDA_EXE):
        print(f"[!] ERROR: The conda executable was not found at: {CONDA_EXE}")
        sys.exit(1)

    envs = scan_filesystem()
    print(f"[*] Found {len(envs)} environments. Starting audit using {CONDA_EXE}...\n")
    
    csv_results = []
    
    # Tracking Sets (Using sets to ensure unique env paths)
    error_envs = set()
    violation_envs = set()
    
    for i, env in enumerate(envs):
        # Print a simple progress dot or status, don't spam unless failure
        # Using \r to overwrite line is cleaner for large lists, 
        # but standard print is safer for logging.
        print(f"[{i+1}/{len(envs)}] Checking: {env}")
        
        packages = get_conda_packages(env)

        if packages == "ERROR":
            print(f"    -> SCAN ERROR (Could not run conda list)")
            error_envs.add(env)
            csv_results.append([env, "ERROR", "N/A", "SCAN_ERROR"])
            continue
        
        if not packages: 
            continue

        env_has_violation = False
        for pkg in packages:
            status = analyze_package(pkg)
            if status != "PASS":
                env_has_violation = True
                print(f"    -> FAIL: {pkg['name']} ({status})")
                csv_results.append([env, pkg['name'], pkg.get('version'), status])
        
        if env_has_violation:
            violation_envs.add(env)

    # --- Generate Output Files ---
    
    # CSV Report
    if csv_results:
        with open(REPORT_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Environment Path", "Package Name", "Version", "Violation Type"])
            writer.writerows(csv_results)

    # Dirty Envs Text File (Combining Errors and Violations)
    all_dirty_envs = sorted(list(error_envs) + list(violation_envs))
    if all_dirty_envs:
        with open(SUMMARY_FILE, 'w') as f:
            for env in all_dirty_envs:
                if env in error_envs:
                    f.write(f"{env} [SCAN ERROR]\n")
                else:
                    f.write(f"{env}\n")

    # --- FINAL SUMMARY BLOCK ---
    total_flagged = len(error_envs) + len(violation_envs)
    
    print("\n" + "="*40)
    print(f"AUDIT SUMMARY REPORT: {HOSTNAME}")
    print("="*40)
    print(f"Envs Found:      {len(envs)}")
    print(f"Flagged Envs:    {total_flagged}")
    print("-" * 20)
    print(f"  - Scan Errors: {len(error_envs)}")
    print(f"  - Violations:  {len(violation_envs)}")
    print("="*40)
    
    print(f"\n[+] Detailed CSV:  {os.path.abspath(REPORT_FILE)}")
    print(f"[+] Dirty List:    {os.path.abspath(SUMMARY_FILE)}")

if __name__ == "__main__":
    main()
