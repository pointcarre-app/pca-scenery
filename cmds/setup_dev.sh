set -e

rm -rf ./env

# install python
~/.pyenv/versions/3.12.3/bin/python -m venv env

# active environment
source env/bin/activate

# packaging
pip install --upgrade pip

# install dependencies
pip install -r requirements.txt
pip install -r dev-requirements.txt

# editable install of scenery
pip install -e .


