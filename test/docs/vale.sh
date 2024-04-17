#!/bin/bash

EXIT_CODE=0

cd ./docs

vale . || EXIT_CODE=$?


notebooks=$(find . -name "*.ipynb" -not -name "*checkpoint*" -not -path "./_**")

if [ -n "$notebooks" ]; then
  echo
  echo "Linting notebooks using nbQA:"
  python -m nbqa vale ${notebooks} --nbqa-shell --nbqa-md || EXIT_CODE=$?
fi

exit $EXIT_CODE
