#!/bin/bash

BUCKET=$1 # take bucket name as first argument
# check if bucket name starts with s3://
if [[ $BUCKET != s3://* ]]; then
  # add s3:// prefix if it's not there
  BUCKET="s3://$BUCKET"
fi

# cache control defaults to 30 days
CACHE_CONTROL=${2:-"public, max-age=2592000"}

# iterate over all files in the bucket, replace cache control with the new value
aws s3 cp $BUCKET $BUCKET --recursive --metadata-directive REPLACE --cache-control $CACHE_CONTROL