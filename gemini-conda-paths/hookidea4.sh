# --- START CUSTOM ISOLATION LOGIC ---

_conda_isolation_hook() {
    if [ -n "$CONDA_PREFIX" ] && [ "$CONDA_DEFAULT_ENV" != "base" ]; then
        export PYTHONNOUSERSITE=1
    else
        unset PYTHONNOUSERSITE
    fi
}

# Append to PROMPT_COMMAND (safely)
# This runs every time the prompt is shown, catching any env change immediately.
if [[ ! "$PROMPT_COMMAND" =~ "_conda_isolation_hook" ]]; then
    export PROMPT_COMMAND="_conda_isolation_hook;$PROMPT_COMMAND"
fi

# --- END CUSTOM ISOLATION LOGIC ---
