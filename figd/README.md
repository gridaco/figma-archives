# `figd`

Simple CLI tool for interacting with the Figma API.

## Commands

### Archive Image Fills from Figma Files

This tool allows you to download and archive image fills from a Figma file, either directly via the Figma API or from a saved API response.

#### Usage

```bash
python cli.py archive image --response <path/to/response.json> [--output <output_dir>] [--file-key <figma_file_key>] [--token <access_token>] [--no-extension]
```

#### Options
- `--response` (required*): Path to the `response.json` file containing the Figma API response with image URLs.
- `--output`, `-o`: Output directory where the images will be saved. Defaults to a temporary directory if not specified.
- `--file-key`: Figma file key to fetch image fills directly from the Figma API.
- `--token`: Figma access token. If not provided, the tool will use the `FIGMA_PERSONAL_ACCESS_TOKEN` environment variable if set.
- `--no-extension`: Save files without extensions (e.g., `image_id` instead of `image_id.png`).

> *You must provide either `--response` or `--file-key`. The `--file-key` option will fetch image fills directly from the Figma API.*

#### Example

```bash
# Using a saved API response
python cli.py archive image --response ./image-response.json --output ./downloads

# Fetching directly from Figma
python cli.py archive image --file-key abc123 --token xyz789

# Save files without extensions
python cli.py archive image --response ./image-response.json --no-extension
```

This will download all image fills from the Figma file and save them in the specified directory (or a temporary directory if not specified), using the correct file extension based on the image type.

> **Note about temporary directories:** If no output directory is specified, the tool creates a temporary directory (e.g., `/tmp/figd_archive_*`). This directory persists until system cleanup (usually on reboot). Make sure to copy any important files from the temporary directory if you need them later.

#### Environment Variables
- `FIGMA_PERSONAL_ACCESS_TOKEN`: Used as the default access token if `--token` is not provided.

---

For more commands and options, run:
```bash
python cli.py --help
```