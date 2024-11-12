#!/bin/bash
set -e

# Ruff
printf "\nRuff\n"
ruff check rehearsal/
ruff check src/

# Mypy
printf "\nMypy\n"
mypy rehearsal
mypy src

# Pydocstyle
printf "\nPydocstyle\n"
# pydocstyle rehearsal
pydocstyle src

