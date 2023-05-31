# sync the sampled archive to s3 with aws cli

## Requirements

- aws cli installed and configured
- aws s3 bucket created
- samples ready to be upload

## Usage

We use separate bucket for storing the file-related json files and image related graphic files and meta.

```bash
# example - for syncing files only (ignore images)
source sync-files.sh /Volumes/Data/DB/figma-samples s3://figma-community-files

# example - for syncing images only (ignore files)
source sync-images.sh /Volumes/Data/DB/figma-samples s3://figma-community-images
```
