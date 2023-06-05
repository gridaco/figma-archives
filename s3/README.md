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

## Notes & Guidelines

### Headers

- DO set `Cache-Control` to `public, max-age=2592000` (30 days, at least) for all files
- DO set `Content-Type` to `application/json` for all json files (even for .json.gz)
- DO set `Content-Encoding` to `gzip` for all .json.gz files

### Compression

- DO compress all json files larger than 5mb with gzip, .json.gz
