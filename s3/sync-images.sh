#!/bin/bash

# Check if both arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: sync-images.sh <local folder> <bucket>"
    exit 1
fi

aws s3 sync $1 $2 \
  --exclude '*' \
  --exclude 'map.json' \
  --exclude 'file.json' \
  --exclude 'data.json' \
  --exclude 'meta.json' \
  --include '*/images/**' \
  --include '*/exports/**'