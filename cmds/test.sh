#!/bin/bash
set -e

# OPTIONAL ARGUMENT: Python version
PYTHON_VERSION=${1:-"3.12.3"} 


echo "Testing with Python $PYTHON_VERSION"
    
# Clean up previous environment and build
rm -rf "./env_test_$PYTHON_VERSION"
rm -rf ./build

# Create and activate new environment
~/.pyenv/versions/$PYTHON_VERSION/bin/python -m venv "env_test_$PYTHON_VERSION"
source "env_test_$PYTHON_VERSION/bin/activate"

# Install and test
pip install --upgrade pip
pip install .
python -m rehearsal

# Cleanup
deactivate
rm -rf "./env_test_$PYTHON_VERSION"
rm -rf ./build

echo "Completed testing with Python $version"
echo "----------------------------------------"


