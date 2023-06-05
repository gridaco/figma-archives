#!/bin/bash

bucket=$1 # take bucket name as first argument
filename=$2 # take file name pattern as second argument

# list all files matching the pattern in the bucket
aws s3 ls s3://$bucket/ --recursive | awk '/'$filename'$/ {print $4}' | while read file
do
  # delete the file
  aws s3 rm s3://$bucket/$file
done
