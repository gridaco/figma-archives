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
  \ --dur-images-archive'path-to-images-archives'
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
│   │   ├── bakes
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
python3 sampler.py
  \ --index='./data/figma-community-popular-20230329.json'
  \ --map='../figma_copy/progress/figma@grida.co.copies.json'
  \ --meta='./data/figma-community-popular-20230329.meta.json'
  \ --output='./data/samples-1000'
  \ --dir-files-archive='./Volumes/WD2TB/Data/figma-scraper-archives'
  \ --dur-images-archive'./Volumes/WD2TB/Data/figma-scraper-image-archives'
  \ --sample=1000
```

````

### Stats

This prints out the status of overall scraping, and the brief stats of the crawled data, including..

- Number of files
- Number of images
  - Average number of images per file
- Number of top level elements
  - Average number of top level elements per file
- Number of Figma pages
  - Average number of Figma pages per file
- Number of screens (top frames with proper sizing)
  - Average number of screens per file
- Number of total elements
  - Average number of total elements per file
- Number of compinents / instances
  - Average number of compinents / instances per file

```bash
python3 stats.py
  \ --index='path-to-index.json'
  \ --dir-archive-files='path-to-files-archive'
  \ --dur-archives-images'path-to-images-archives'
````
