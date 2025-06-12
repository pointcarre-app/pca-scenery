#!/bin/bash
set -e

# Ruff
printf "\n# Ruff\n"
printf "\n## rehearsal\n"
python -m ruff check rehearsal/
printf "\n## src\n"
python -m ruff check src/

# Mypy
printf "\n# Mypy\n"
printf "\n## rehearsal\n"
python -m mypy rehearsal
printf "\n## src\n"
python -m mypy src

# Pydocstyle
printf "\nPydocstyle\n"
# pydocstyle rehearsal
pydocstyle src

