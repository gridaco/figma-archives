# Figma Archiver

This is a module to archive (download) the Figma file via official API.

Donwload once, with full data, so we can use it offline and won't need to access Figma API again.

## Usage

```bash
python3 files.py -f <mapfile> -t <figma_token> -o <output_dir>

# examples
python3 files.py -f ../figma_copy/progress/your@figma-account.com.copies.json

# replacing
python3 files.py -f ../path/to/map.json --replace


# fetching only images (after fetching files)
python3 images.py --src='./downloads/*.json'
```

Alternatively, you can set the -t (access token) under `.env`

```
FIGMA_ACCESS_TOKEN=<your-token>
```

We use requests for API call, (since it's a simple GET request, we don't need to use axios or other libraries)

[Learn how to get your Figma access token here](https://grida.co/docs/with-figma/guides/how-to-get-personal-access-token)

## References

- https://www.figma.com/developers/api

```

```

## Scripts

### `minify.py`

This script is to minify the JSON files, so we can save some space.

```bash
python3 ./scripts/minify.py\
  ./downloads\
  --pattern='{key}.json'\
  --output='./downloads/minified'\
  --output-pattern='{key}.min.json'\
  --max=1000

  # --output-pattern='{key}.min.json' to create new with .min.json
  # --output-pattern='{key}.json' to replace
```

Note that this will handle all json files with matching pattern, so make sure you have the right pattern and the directory is correct.

```bash
# Example usage on external drive
python3 ./scripts/minify.py\
  /Volumes/WDB2TB/Data/figma-scraper-archives\
  --pattern='{key}.json'\
  --output=/Volumes/WDB2TB/Data/figma-scraper-archives.min\
  --output-pattern='{key}.json'
```
