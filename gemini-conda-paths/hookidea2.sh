# 1. Define the logic function
_conda_isolation_check() {
    if [ -n "$CONDA_PREFIX" ] && [ "$CONDA_DEFAULT_ENV" != "base" ]; then
        export PYTHONNOUSERSITE=1
    else
        unset PYTHONNOUSERSITE
    fi
}

# 2. Wrap the 'conda' command to run the check immediately after use
conda() {
    # Run the real conda command
    command conda "$@"
    
    # Store the exit code of conda so we don't lose it
    local exit_code=$?
    
    # Run our isolation check
    _conda_isolation_check
    
    # Return the original exit code
    return $exit_code
}

# 3. Export the function so it works in subshells
export -f conda

# 4. Run the check once immediately (in case the user logs in directly to an env)
_conda_isolation_check
