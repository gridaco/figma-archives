## How to use

### Community Indexer

```bash
scrapy crawl figma_spider --nolog -a target=recent
scrapy crawl figma_spider --nolog -a target=popular
```

**Sorting**

Note: this spider does not crawl paid files

- [popular](https://www.figma.com/community/files/figma/free/popular) - figma community lists the popular file with download (copies) count
- [recent](https://www.figma.com/community/files/figma/free/new) - figma community lists the recent file with last updated date (not created date if initial upload)
- [trending](https://www.figma.com/community/files/figma/free/) - the logic behind is unknown, but it seems to be based on recent number of copies

**Indexing CRON workflow & Cancelation tokens**

Providing a cancelation token for `recent` is tricky. Since recent both contains newly uploaded item and updated item, we can't use last-uploaded-item as a cencel parameter. - this case, if the new item is updated with a very low chance, we will not be able to reach the new items created between the first entry and the second entry.

To overcome this, we provide lastest n items as a cancelation token. if all n items are found on the second entry, the spider will stop, n being 30 (items diplayed in a single page scrol) by default, for cron job that runs twice a day, it can be smaller on shorter interval. - explanation? - the chances are very low that all n items are updated in next interval.

These cancelation tokens are saved at [data/.spider/index-cancelation-tokens.json](../data/.spider/index-cancelation-tokens.json), being replaced with the first n items on the next crawl, after all items are saved. and referenced as a new cancelation tokens on the next run.

You can see index spider cron job at [.github/workflows/figma-index.spider.yml](../.github/workflows/figma-index-spider.yml)

This workflow isn't meant to crawl all data from scratch, but instead it is only valid to be used with existing index. - this part, the initial full-indexing is done by the maintainers

### Meta Spider

```bash
scrapy crawl meta_spider --nolog
\ -a index='output.popular.json'
\ -o output.popular.meta.json
```

<!-- For us, the maintainers -->
<!-- scrapy crawl meta_spider --nolog -a index='../data/latest/index.json' -o ../data/latest/meta.json -->
