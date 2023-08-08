#!/bin/bash

cd ../../tutorials

vale .

echo
echo "Linting notebooks using nbQA:"

notebooks=$(find . -name "*.ipynb" -not -name "*checkpoint*" -not -path "./_**")

python -m nbqa vale ${notebooks} --nbqa-shell --nbqa-md
