# Figma Archiver

This is a module to archive (download) the Figma file via official API.

Donwload once, with full data, so we can use it offline and won't need to access Figma API again.

## Usage

```bash
python3 main.py -f <list_file> -t <figma_token> -o <output_dir>

# for example
python3 main.py -f ../figma_copy/progress/figma@grida.co.copies.json

# fetching only files
python3 files.py -f ../the_rest_is_the_same
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
