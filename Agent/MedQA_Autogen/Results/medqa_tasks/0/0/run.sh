#
echo RUN.SH STARTING !#!#
export AUTOGEN_TESTBED_SETTING="Native"
echo "autogenbench version: 0.0.3" > timestamp.txt

# Create and activate the virtual environment
# This is called in a subprocess, and will not impact the parent
/opt/homebrew/anaconda3/envs/CAIN/bin/python3.11 -m venv .autogenbench_venv
. .autogenbench_venv/bin/activate

# Run the global init script if it exists
if [ -f global_init.sh ] ; then
    . ./global_init.sh
fi

# Run the scenario init script if it exists
if [ -f scenario_init.sh ] ; then
    . ./scenario_init.sh
fi

# Run the scenario
pip install -r requirements.txt
echo SCENARIO.PY STARTING !#!#
timeout --preserve-status --kill-after 1830s 1800s python scenario.py
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo SCENARIO.PY EXITED WITH CODE: $EXIT_CODE !#!#
else
    echo SCENARIO.PY COMPLETE !#!#
fi

# Clean up
if [ -d .cache ] ; then
    rm -Rf .cache
fi

if [ -d __pycache__ ] ; then
    rm -Rf __pycache__
fi

# Run the scenario finalize script if it exists
if [ -f scenario_finalize.sh ] ; then
    . ./scenario_finalize.sh
fi

# Run the global finalize script if it exists
if [ -f global_finalize.sh ] ; then
    . ./global_finalize.sh
fi

# We don't need to deactivate the venv because it's
# contained in the subprocess; but we should clean it up
if [ -d .autogenbench_venv ] ; then
    rm -Rf .autogenbench_venv
fi

echo RUN.SH COMPLETE !#!#
