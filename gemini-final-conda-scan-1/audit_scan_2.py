import os
import json
import subprocess
import csv
import socket
from datetime import datetime

# --- CONFIGURATION ---

# The specific internal URL you use to proxy conda-forge
# Example: "nexus.mycompany.com"
INTERNAL_NEXUS_URL = "nexus.yourdomain.com" 

# STRICT ALLOW LIST
# If the channel URL does not contain one of these strings, it fails.
ALLOWED_INDICATORS = ["conda-forge", INTERNAL_NEXUS_URL]

# KNOWN BAD INDICATORS (For better error reporting)
# These clearly indicate the proprietary Anaconda repo.
ANACONDA_INDICATORS = ["repo.anaconda.com", "pkgs/main", "pkgs/r", "pkgs/msys2", "defaults"]

# Roots to scan (Recursive)
SCAN_ROOTS = ["/home", "/opt", "/usr/local"]

# Output file for the report
REPORT_FILE = f"conda_audit_report_{socket.gethostname()}.csv"

# ---------------------

def get_conda_packages(env_path):
    """
    Runs conda list in JSON format for a specific prefix.
    """
    try:
        # Check if python exists in this env to verify it's a valid target
        # (Some conda-meta folders might be stale/broken)
        if not os.path.exists(os.path.join(env_path, "conda-meta")):
            return None

        result = subprocess.run(
            ["conda", "list", "-p", env_path, "--json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # If conda list fails, we flag the env as "UNSCANNABLE"
            return "ERROR"
            
        return json.loads(result.stdout)
    except Exception as e:
        return "ERROR"

def analyze_package(pkg):
    name = pkg.get('name', 'unknown')
    channel = pkg.get('channel')
    version = pkg.get('version', '?')

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
        # It's not empty, not explicitly Anaconda, but not in our allowed list either.
        # Could be pypi, or a user's personal channel.
        if channel == "pypi":
             # Decide if you want to allow pip packages. usually harmless for Anaconda license
             # but technically not "conda-forge". Set to PASS or RISK as needed.
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
            # Optimization: skip hidden directories like .cache or .local to save time?
            # For now we scan everything.
            
            if "conda-meta" in dirnames:
                env_path = dirpath
                discovered_envs.append(env_path)
                # Don't recurse deeper into this env
                dirnames.remove("conda-meta") 
                
    return discovered_envs

def main():
    if os.geteuid() != 0:
        print("[-] WARNING: Not running as root. You will miss user environments.")
        print("[-] Please run with sudo.\n")

    envs = scan_filesystem()
    print(f"[*] Found {len(envs)} environments. Starting audit...\n")
    
    results = []
    
    for i, env in enumerate(envs):
        print(f"[{i+1}/{len(envs)}] Checking: {env}")
        packages = get_conda_packages(env)

        if packages == "ERROR":
            print(f"    ! ERROR: Could not run conda list on {env}")
            results.append([env, "ERROR", "N/A", "N/A"])
            continue
        
        if not packages: # Empty env
            continue

        env_dirty = False
        for pkg in packages:
            status = analyze_package(pkg)
            if status != "PASS":
                env_dirty = True
                print(f"    -> FAIL: {pkg['name']} ({status})")
                results.append([env, pkg['name'], pkg.get('version'), status])
    
    # Write Report
    if results:
        print(f"\n[!] VIOLATIONS FOUND. Writing report to {REPORT_FILE}...")
        with open(REPORT_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Environment Path", "Package Name", "Version", "Violation Type"])
            writer.writerows(results)
        print(f"[!] Report saved. You have work to do.")
    else:
        print("\n[+] SUCCESS: No violations found. All environments conform to strict policy.")

if __name__ == "__main__":
    main()
