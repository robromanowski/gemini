# Check if we are running in Bash before defining Bash-specific functions
if [ -n "$BASH_VERSION" ]; then

    _conda_isolation_check() {
        if [ -n "$CONDA_PREFIX" ] && [ "$CONDA_DEFAULT_ENV" != "base" ]; then
            export PYTHONNOUSERSITE=1
        else
            unset PYTHONNOUSERSITE
        fi
    }

    conda() {
        # Run the real conda command
        command conda "$@"
        local exit_code=$?
        
        # Run the isolation check
        _conda_isolation_check
        
        return $exit_code
    }

    # Exporting functions is only valid in Bash
    export -f conda

    # Run the check once immediately
    _conda_isolation_check

fi
