import os
import json
import subprocess
import csv
import socket
import sys

# --- CONFIGURATION ---

# !!! IMPORTANT: PUT THE FULL PATH TO CONDA HERE !!!
# Run 'which conda' to find this if you haven't already.
CONDA_EXE = "/opt/anaconda3/bin/conda" 

# Your internal URL
INTERNAL_NEXUS_URL = "nexus.yourdomain.com" 

# STRICT ALLOW LIST
ALLOWED_INDICATORS = ["conda-forge", INTERNAL_NEXUS_URL]

# KNOWN BAD INDICATORS
ANACONDA_INDICATORS = ["repo.anaconda.com", "pkgs/main", "pkgs/r", "pkgs/msys2", "defaults"]

# Roots to scan
SCAN_ROOTS = ["/home", "/opt", "/usr/local"]

# Output files
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
            print(f"    ! STDERR: {result.stderr.strip()}")
            return "ERROR"
            
        return json.loads(result.stdout)
    except FileNotFoundError:
        print(f"    ! CRITICAL: The script cannot find the conda executable at {CONDA_EXE}")
        sys.exit(1)
    except Exception as e:
        print(f"    ! EXCEPTION: {e}")
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
    dirty_envs_set = set() # To store unique bad env paths
    
    for i, env in enumerate(envs):
        print(f"[{i+1}/{len(envs)}] Checking: {env}")
        packages = get_conda_packages(env)

        if packages == "ERROR":
            print(f"    ! ERROR: Could not run conda list on {env}")
            # We add ERROR envs to the dirty list just in case you want to manually review them
            dirty_envs_set.add(f"{env} (SCAN ERROR)")
            csv_results.append([env, "ERROR", "N/A", "N/A"])
            continue
        
        if not packages: 
            continue

        for pkg in packages:
            status = analyze_package(pkg)
            if status != "PASS":
                # Add to CSV list
                csv_results.append([env, pkg['name'], pkg.get('version'), status])
                # Add to high-level dirty list
                dirty_envs_set.add(env)

    # --- Write Detailed CSV ---
    if csv_results:
        print(f"\n[!] VIOLATIONS FOUND.")
        print(f"    Writing detailed report to: {REPORT_FILE}")
        with open(REPORT_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Environment Path", "Package Name", "Version", "Violation Type"])
            writer.writerows(csv_results)

    # --- Write Summary Text File ---
    if dirty_envs_set:
        print(f"    Writing high-level summary to: {SUMMARY_FILE}")
        with open(SUMMARY_FILE, 'w') as f:
            for env in sorted(dirty_envs_set):
                f.write(f"{env}\n")
    else:
        print("\n[+] SUCCESS: No violations found.")

if __name__ == "__main__":
    main()
