#!/bin/bash
set -e

# Ruff
printf "\n\nRuff"
ruff check rehearsal/
ruff check src/

# Mypy
printf "\n\nMypy"
mypy rehearsal
mypy src

# Pydocstyle
printf "\n\nPydocstyle"
pydocstyle rehearsal
pydocstyle src

