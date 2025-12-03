import os
import json
import subprocess
import sys

# --- CONFIGURATION ---

# Add your internal nexus URL snippet here. 
# The script checks if this string appears in the channel URL.
INTERNAL_NEXUS_URL = "nexus.yourdomain.com" 

# Valid indicators. If the channel contains these, it passes.
# If the channel is blank/None, or contains 'pkgs/main', 'defaults', etc., it fails.
ALLOWED_CHANNELS = ["conda-forge", INTERNAL_NEXUS_URL]

# Directories to scan for environments (Recursive)
# Add any other paths where users might store envs (e.g., /data, /usr/local)
SCAN_ROOTS = ["/home", "/opt/anaconda", "/opt/miniconda"]

# ---------------------

def get_conda_packages(env_path):
    """
    Runs conda list in JSON format for a specific prefix.
    """
    try:
        # We use -p to target the specific path found on disk
        result = subprocess.run(
            ["conda", "list", "-p", env_path, "--json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"[!] Error reading env {env_path}: {result.stderr}")
            return None
            
        return json.loads(result.stdout)
    except Exception as e:
        print(f"[!] Exception scanning {env_path}: {e}")
        return None

def is_valid_channel(channel_url):
    """
    Returns True if the channel matches our Allow List.
    Returns False if channel is None, blank, 'defaults', 'pypi', etc.
    """
    if not channel_url:
        # This catches the 'blank' column issue you mentioned
        return False
    
    # Check if any allowed string is inside the channel URL
    for allowed in ALLOWED_CHANNELS:
        if allowed in channel_url:
            return True
            
    return False

def scan_filesystem():
    discovered_envs = []
    print(f"[*] Scanning file system for 'conda-meta' directories in: {SCAN_ROOTS}...")
    
    for root_dir in SCAN_ROOTS:
        if not os.path.exists(root_dir):
            continue
            
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Optimization: Don't walk into the envs themselves, just look for meta
            if "conda-meta" in dirnames:
                # The environment root is the folder containing conda-meta
                env_path = dirpath
                discovered_envs.append(env_path)
                # Don't recurse deeper into this env
                dirnames.remove("conda-meta") 
                
    return discovered_envs

def main():
    if os.geteuid() != 0:
        print("[-] Warning: Not running as root. You may miss user environments due to permission errors.")

    envs = scan_filesystem()
    print(f"[*] Found {len(envs)} environments. Starting audit...\n")
    print("-" * 60)

    dirty_envs_count = 0

    for env in envs:
        packages = get_conda_packages(env)
        if not packages:
            continue

        bad_packages = []

        for pkg in packages:
            name = pkg.get('name')
            channel = pkg.get('channel')
            
            # Skip pip packages if you only care about conda channels
            # Usually pip packages have channel: "<develop>" or "pypi"
            # If you want to allow pypi, add 'pypi' to ALLOWED_CHANNELS above.
            
            if not is_valid_channel(channel):
                bad_packages.append({
                    "name": name, 
                    "channel": channel if channel else "[BLANK/DEFAULTS]"
                })

        if bad_packages:
            dirty_envs_count += 1
            print(f"FAIL: {env}")
            for bad in bad_packages:
                print(f"    - Pkg: {bad['name']:<20} Channel: {bad['channel']}")
            print("-" * 60)
        else:
            # Optional: Print passing envs
            # print(f"PASS: {env}")
            pass

    print(f"\n[*] Audit Complete.")
    print(f"[*] Total Envs Scanned: {len(envs)}")
    print(f"[*] Dirty Envs Found:   {dirty_envs_count}")

if __name__ == "__main__":
    main()
