#!/bin/bash

# Script to find parquet-avro and avro JAR files across the entire filesystem using fd.

# --- Configuration ---
# Regex patterns to match the JAR files at the end of the path
# We escape the dot in .jar (\.) and use .* to match any characters for the version
PARQUET_AVRO_PATTERN='parquet-avro.*\.jar$'
AVRO_PATTERN='avro-.*\.jar$'
SEARCH_PATH='/' # Search the entire filesystem starting from root

# --- Check if fd command exists ---
if ! command -v fd &> /dev/null; then
    echo "Error: 'fd' command not found." >&2
    echo "Please install fd: https://github.com/sharkdp/fd" >&2
    exit 1
fi

# --- Inform the User ---
echo "Starting search for Parquet and Avro JAR files using fd."
echo "Search path: ${SEARCH_PATH}"
echo "This will scan the entire filesystem and may take a significant amount of time."
echo "You may see 'Permission denied' errors for directories you don't have access to."
echo "For a complete search, you might need to run this script with sudo:"
echo "sudo $0"
echo "-----------------------------------------------------"

# --- Perform the Search ---

echo "[INFO] Searching for Parquet Avro JARs (${PARQUET_AVRO_PATTERN})..."
# --hidden: Search hidden files and directories
# --no-ignore: Do not respect .gitignore, .ignore, .fdignore files
# --full-path: Match the pattern against the full path
# The search path '/' is provided at the end
fd --hidden --no-ignore --full-path "${PARQUET_AVRO_PATTERN}" "${SEARCH_PATH}"
echo # Add a newline for clarity
echo "[INFO] Searching for Avro JARs (${AVRO_PATTERN})..."
fd --hidden --no-ignore --full-path "${AVRO_PATTERN}" "${SEARCH_PATH}"

echo "-----------------------------------------------------"
echo "[INFO] Search complete."
echo "Review the paths above to identify the versions (e.g., avro-1.11.1.jar)."

exit 0
