## How to use

### Community Indexer

```bash
scrapy crawl figma_spider --nolog -a target=recent
scrapy crawl figma_spider --nolog -a target=popular
```

**Sorting**

- [popular](https://www.figma.com/community/files/figma/free/popular) - figma community lists the popular file with download (copies) count
- [recent](https://www.figma.com/community/files/figma/free/new) - figma community lists the recent file with last updated date (not created date if initial upload)
- [trending](https://www.figma.com/community/files/figma/free/) - the logic behind is unknown, but it seems to be based on recent number of copies

### Meta Spider

```bash
scrapy crawl meta_spider --nolog
\ -a index='output.popular.json'
\ -o output.popular.meta.json
```

<!-- For us, the maintainers -->
<!-- scrapy crawl meta_spider --nolog -a index='../data/latest/index.json' -o ../data/latest/meta.json -->
