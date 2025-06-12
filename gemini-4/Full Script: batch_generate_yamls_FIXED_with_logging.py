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

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Filtering Configuration (for fallback method) ---
FILTER_OUT_PACKAGES = {
    "_libgcc_mutex", "_openmp_mutex", "bzip2", "ca-certificates",
    "ld_impl_linux-64", "libffi", "libgcc-ng", "libgomp", "libstdcxx-ng",
    "libuuid", "ncurses", "openssl", "readline", "sqlite", "tk", "tzdata",
    "xz", "zlib", "certifi", "setuptools", "pip", "wheel", "six", "zipp",
    # Add more common low-level dependencies here if needed
}
HISTORY_LENGTH_THRESHOLD = 50
BUILD_STRING_RE = re.compile(r"=\w*h[0-9a-f]{7,}|=\w+_\d+<span class="math-inline">\|\=main</span>")

# --- Helper Functions ---
# (All helper functions like path2str, run_conda_command, get_pip_deps_from_export, etc. remain the same)
winOS = sys.platform == "win32"
def path2str0(p: Path, win_os: bool = True): s = str(p) if win_os else p.as_posix(); return s
path2str = partial(path2str0, win_os=winOS)

def run_conda_command(conda_exe_path: str, args_list: list, env_path: Path = None, use_shell: bool = False):
    command = [str(conda_exe_path)] + args_list
    if env_path: command.extend(['-p', path2str(env_path)])
    cmd_str_for_log = " ".join(command)
    cmd_exec = cmd_str_for_log if use_shell else command
    log.info(f"  Running: {cmd_str_for_log}")
    try:
        proc = subprocess.run(cmd_exec, capture_output=True, text=True, check=True, shell=use_shell, timeout=180)
        log.debug(f"  Command stdout:\n{proc.stdout[:500]}...")
        return proc.stdout
    except subprocess.CalledProcessError as e: log.error(f"  ERROR running command: {cmd_str_for_log}\n  Stderr: {e.stderr}"); raise
    except FileNotFoundError: log.error(f"  ERROR:
