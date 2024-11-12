#!/bin/bash
set -e

# Ruff
printf "\nRuff\n"
python -m ruff check rehearsal/
python -m ruff check src/

# Mypy
printf "\nMypy\n"
python -m mypy rehearsal
python -m mypy src

# Pydocstyle
printf "\nPydocstyle\n"
# pydocstyle rehearsal
pydocstyle src

