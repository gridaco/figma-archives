# Sampler

This is use to sample the data from the scraped data, including the following data.

## Usage

### Sampling

Samples the input from multiple sources to one output directory.

Doing this will convert each item's `:filekey` to the original community id from the index file.

```bash
python3 sampler.py
  \ --index='path-to-index.json'
  \ --map='path-to-map.json'
  \ --meta='path-to-meta.json'
  \ --output='path-to-out-dir'
  \ --dir-files-archive='path-to-files-archive'
  \ --dir-images-archive'path-to-images-archives'
  \ --sample=1000 # or --sample-all
```

**`--sample-all`**

This is also used for creating final output, files are copied to follow original community file ids.

**The Output**

Once complete, the output directory will be populated with the following files.

```
├── :root (output directory)
│   ├── :id (community id)
│   │   ├── file.json
│   │   ├── thumbnail.png
│   │   ├── images
│   │   │   ├── :hash.png
│   │   │   ├── :hash.png
│   │   │   ├── :hash.png
│   │   ├── exports
│   │   │   ├── :node.png
│   │   │   ├── :node.png
│   │   │   ├── :node.png
│   │   ├── map.json
│   │   ├── meta.json
│   ├── :id (community id)
│   │   ├── ...
```

**Example**

```bash
# sampling 5k.min
python3 sampler.py\
  --index='../data/samples/5k'\
  --output='/Volumes/WDB2TB/Data/figma-samples-5k'\
  --dir-files-archive='/Volumes/WDB2TB/Data/figma-scraper-archives'\
  --skip-images\
  --sample=5000

# sampling for archives (all)
python3 sampler.py\
  --index='../data/latest'\
  --output='/Volumes/WDB2TB/Data/figma-archives'\
  --dir-files-archive='/Volumes/WDB2TB/Data/figma-scraper-archives'\
  --dir-images-archive='/Volumes/WDB2TB/Data/figma-scraper-image-archives'

# sampling only images
python3 sampler.py\
  --index='../data/samples/500'\
  --output='/Volumes/WDB2TB/Data/figma-image-samples-500'\
  --dir-files-archive='/Volumes/WDB2TB/Data/figma-scraper-archives'\
  --dir-images-archive='/Volumes/WDB2TB/Data/figma-archives-images'\
  --only-images
```
