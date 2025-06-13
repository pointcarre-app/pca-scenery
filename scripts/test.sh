#!/bin/bash
set -e

# OPTIONAL ARGUMENT: Python version
PYTHON_VERSION=${1:-"3.12.3"} 


printf "Testing with Python $PYTHON_VERSION\n"
    
# Clean up previous environment and build
rm -rf "./env_test_$PYTHON_VERSION"
rm -rf ./build

# Create and activate new environment
~/.pyenv/versions/$PYTHON_VERSION/bin/python -m venv "env_test_$PYTHON_VERSION"
source "env_test_$PYTHON_VERSION/bin/activate"

# Install (non editable)
pip install --upgrade pip
pip install .

# Prepare db
cd rehearsal/django_project
python manage.py makemigrations
python manage.py migrate
cd ../..

# Test
printf "\n\nRehearsal\n"
python -m rehearsal

# Cleanup
deactivate
rm -rf "./env_test_$PYTHON_VERSION"
rm -rf ./build

echo "Completed testing with Python $version"
echo "----------------------------------------"


