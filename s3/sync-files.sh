#!/bin/bash

# Check if both arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: sync-files.sh <local folder> <bucket>"
    exit 1
fi

aws s3 sync $1 $2 \
  --exclude '*' \
  --include '*/file.json' \
  --include '*/file.json.gz' \
  --include '*/map.json' \
  --include '*/meta.json' \
  --exclude '*/images/**' \
  --exclude '*/exports/**'