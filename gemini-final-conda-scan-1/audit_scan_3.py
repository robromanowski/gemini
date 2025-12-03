import os
import json
import subprocess
import csv
import socket
import sys

# --- CONFIGURATION ---

# !!! IMPORTANT: PUT THE FULL PATH TO CONDA HERE !!!
# Run 'which conda' in your terminal to find this.
# Examples: "/opt/anaconda3/bin/conda" or "/root/miniconda3/condabin/conda"
CONDA_EXE = "/opt/anaconda3/bin/conda"  # <--- UPDATE THIS

# Your internal URL
INTERNAL_NEXUS_URL = "nexus.yourdomain.com" 

# STRICT ALLOW LIST
ALLOWED_INDICATORS = ["conda-forge", INTERNAL_NEXUS_URL]

# KNOWN BAD INDICATORS
ANACONDA_INDICATORS = ["repo.anaconda.com", "pkgs/main", "pkgs/r", "pkgs/msys2", "defaults"]

# Roots to scan
SCAN_ROOTS = ["/home", "/opt", "/usr/local"]

# Output file
REPORT_FILE = f"conda_audit_report_{socket.gethostname()}.csv"

# ---------------------

def get_conda_packages(env_path):
    """
    Runs conda list in JSON format for a specific prefix using the absolute path to conda.
    """
    try:
        # We use the absolute path CONDA_EXE here
        result = subprocess.run(
            [CONDA_EXE, "list", "-p", env_path, "--json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Print the actual stderr so we know WHY it failed
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

    # Case 1: Channel is empty/null (Very common for old 'defaults' packages)
    if not channel:
        return "RISK_EMPTY_CHANNEL"

    # Case 2: Explicit Anaconda Repo
    if any(bad in channel for bad in ANACONDA_INDICATORS):
        return "VIOLATION_ANACONDA_DEFAULT"

    # Case 3: Not in our Allow List
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
    
    # Pre-flight check
    if not os.path.isfile(CONDA_EXE):
        print(f"[!] ERROR: The conda executable was not found at: {CONDA_EXE}")
        print("[!] Please edit the 'CONDA_EXE' variable in the script.")
        sys.exit(1)

    envs = scan_filesystem()
    print(f"[*] Found {len(envs)} environments. Starting audit using {CONDA_EXE}...\n")
    
    results = []
    
    for i, env in enumerate(envs):
        print(f"[{i+1}/{len(envs)}] Checking: {env}")
        packages = get_conda_packages(env)

        if packages == "ERROR":
            print(f"    ! ERROR: Could not run conda list on {env}")
            results.append([env, "ERROR", "N/A", "N/A"])
            continue
        
        if not packages: 
            continue

        for pkg in packages:
            status = analyze_package(pkg)
            if status != "PASS":
                print(f"    -> FAIL: {pkg['name']} ({status})")
                results.append([env, pkg['name'], pkg.get('version'), status])
    
    if results:
        print(f"\n[!] VIOLATIONS FOUND. Writing report to {REPORT_FILE}...")
        with open(REPORT_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Environment Path", "Package Name", "Version", "Violation Type"])
            writer.writerows(results)
    else:
        print("\n[+] SUCCESS: No violations found.")

if __name__ == "__main__":
    main()
