## How to use

### Community Indexer

```bash
scrapy crawl figma_spider --nolog -a target=recent
scrapy crawl figma_spider --nolog -a target=popular
```

### Meta Spider

```bash
scrapy crawl meta_spider --nolog
\ -a index='output.popular.json'
\ -o output.popular.meta.json
```

<!-- For us, the maintainers -->
<!-- scrapy crawl meta_spider --nolog -a index='../data/figma-community-popular-20230329.json' -o ../data/figma-community-popular-20230329.meta.json -->
