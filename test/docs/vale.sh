#!/bin/bash

EXIT_CODE=0

cd ./docs

vale . || EXIT_CODE=$?

echo
echo "Linting notebooks using nbQA:"

notebooks=$(find . -name "*.ipynb" -not -name "*checkpoint*" -not -path "./_**")

python -m nbqa vale ${notebooks} --nbqa-shell --nbqa-md || EXIT_CODE=$?

exit $EXIT_CODE
