# Manually load global conda config (with custom isolation fix)
if [ -f "/usr/app/miniforge3/etc/profile.d/conda.sh" ]; then
    . "/usr/app/miniforge3/etc/profile.d/conda.sh"
fi
