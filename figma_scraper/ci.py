import subprocess
import click
from datetime import datetime
import json
import jsonlines
import os
from scrapy import signals
from scrapy.signalmanager import dispatcher
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from figma_scraper.spiders import figma_spider
from figma_scraper.spiders import meta_spider
from multiprocessing import Process


@click.group()
def cli():
    pass


__dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(__dir, '../data')  # path to data directory

cancelation_tokens_file = os.path.join(
    DATA_DIR, '.spider/index/crawler.lock')

master_index_file = os.path.join(DATA_DIR, 'latest/index.json')
master_meta_file = os.path.join(DATA_DIR, 'latest/meta.jsonl')


def get_cancelation_tokens():
    with open(cancelation_tokens_file, "r", encoding="utf-8") as f:
        # remove empty lines
        ids = [line.strip() for line in f if line.strip()]
        cancelation_tokens = set(ids)
        return cancelation_tokens


def set_cancelation_tokens(tokens):
    with open(cancelation_tokens_file, "w", encoding="utf-8") as f:
        f.write("\n".join(tokens))
        return True


class FigmaSiderCollector(object):
    def __init__(self):
        self.items = []

    def item_scraped(self, item, spider):
        self.items.append(item)
        print(f"Item scraped: {item['id']}")


@cli.command('index')
@click.option('--timeout-minutes', default=0, help='Timeout in minutes (0 for no timeout)')
def ci_index(timeout_minutes):
    cancelation_tokens = get_cancelation_tokens()
    cancelation_tokens_count = len(cancelation_tokens)

    sort = 'recent'

    now = datetime.now()
    iso_now = now.replace(microsecond=0).isoformat()
    feed = os.path.join(__dir, f'out/index@{iso_now}.jsonl')
    log = f'out/spider-index-{iso_now}.log'

    def spider_closed(spider):
        # put your logic here
        stats = spider.crawler.stats.get_stats()
        next_cancelation_tokens = stats['ci/next-cancelation-tokens']
        print("Spider closed: %s" % spider.name)

        if next_cancelation_tokens and len(next_cancelation_tokens) >= cancelation_tokens_count:
            set_cancelation_tokens(next_cancelation_tokens)
        else:
            print(
                f"New cancelation tokens ({len(next_cancelation_tokens)}) were provided, but they are not enough to replace the old ones ({len(cancelation_tokens)}).")

    process = CrawlerProcess({
        **get_project_settings(),
        "LOG_ENABLED": True,
        "LOG_FILE": log,
        "LOG_LEVEL": "WARNING",
        "CLOSESPIDER_TIMEOUT": timeout_minutes * 60,
        "FEEDS": {
            feed: {
                "format": "jsonlines",
                "encoding": "utf8",
            },
        },
    })

    collector = FigmaSiderCollector()
    dispatcher.connect(collector.item_scraped, signal=signals.item_scraped)
    dispatcher.connect(spider_closed, signal=signals.spider_closed)

    # Start your spider
    process.crawl(figma_spider.FigmaSpider, target=sort,
                  cancelation_tokens=cancelation_tokens)

    process.start()  # the script will block here until the crawling is finished

    # after closed.
    # read the feed file, compare with the main index file, add new items to the main index file
    with open(feed, "r", encoding="utf-8") as f:
        data_scraped = [json.loads(line) for line in f]
        ids_scraped = set([item['id'] for item in data_scraped])

    with open(master_index_file, "a+", encoding="utf-8") as f:
        f.seek(0)  # move the file pointer to the beginning of the file
        data_existing = [json.loads(line) for line in f]
        ids_existing = set([item['id'] for item in data_existing])

        # filter out existing ids from scraped ids
        ids_new = ids_scraped - ids_existing

        # filter out scraped data with existing ids
        data_new = [item for item in data_scraped if item['id'] in ids_new]

        # move the file pointer back to the end of the file
        f.seek(0, os.SEEK_END)

        # append new data to the main index file
        f.write("\n".join([json.dumps(item) for item in data_new]))
        # write trailing newline
        f.write("\n")

    print(
        f"Crawling index finished. Total: {len(ids_scraped)}, New Items discovered: {len(ids_new)}")

    return {
        "feed": feed,
        "data": data_new,
        "data*": data_scraped,
    }


def update_meta(timeout_minutes, index: list):

    now = datetime.now()
    iso_now = now.replace(microsecond=0).isoformat()
    feed = os.path.join(__dir, f'out/meta@{iso_now}.jsonl')
    # log = f'out/spider-meta-{iso_now}.log'

    process = CrawlerProcess({
        **get_project_settings(),
        "LOG_ENABLED": True,
        # "LOG_FILE": log,
        "LOG_LEVEL": "ERROR",
        "CLOSESPIDER_TIMEOUT": timeout_minutes * 60,
        "FEEDS": {
            feed: {
                "format": "jsonlines",
                "encoding": "utf8",
            },
        },
    })

    process.crawl(meta_spider.FigmaMetaSpider, index=index)
    process.start()  # the script will block here until the crawling is finished

    print("Crawling meta finished.")
    
    # after finished
   
    # read the feed jsonlines and store in a dictionary for quick lookup
    with jsonlines.open(feed) as reader:
        new_data = {item["id"]: item for item in reader}
    print(f"New data: {len(new_data)}")

    updated_data = []
    existing_ids = set()
    updated_count = 0
    new_count = 0

    # open the master meta file and update in place if necessary
    with jsonlines.open(master_meta_file) as reader:
        for item in reader:
            existing_ids.add(item["id"])
            # if the item exists in the new data, update the item
            if item["id"] in new_data:
                item.update(new_data[item["id"]])
                updated_count += 1
            updated_data.append(item)

    # append new items at the end of updated_data
    for item_id, item in new_data.items():
        if item_id not in existing_ids:
            updated_data.append(item)
            new_count += 1

    # save the updated data to the master meta file
    with jsonlines.open(master_meta_file, mode='w') as writer:
        writer.write_all(updated_data)

    print(f"Original data count: {len(existing_ids)}")
    print(f"Updated data count: {updated_count}")
    print(f"Newly inserted data count: {new_count}")
    print(f"Final data count: {len(updated_data)}")

@cli.command("meta")
@click.option('--timeout-minutes', default=0, help='Timeout in minutes (0 for no timeout)')
@click.option('--index', default=None, help='Index file to use', type=click.Path(exists=True, dir_okay=False))
def ci_meta(timeout_minutes, index):
    # read the index file (jsonlines)
    with jsonlines.open(index) as reader:
        index = [item for item in reader]

    update_meta(timeout_minutes=timeout_minutes, index=index)


@cli.command("all")
@click.option('--timeout-minutes', default=0, help='Timeout in minutes (0 for no timeout)')
@click.option('--mock-ci', default=False, help='Mock the CI env', type=bool, is_flag=True)
def ci_all(timeout_minutes, mock_ci):
    """
    Runs the meta spider after the index spider has finished.
    """

    # set the CI env if mock_ci is set
    if mock_ci:
        os.environ["CI"] = "true"

    CI = os.environ.get('CI', False)

    # 6:4 allocation
    spider_index_timeout_factor = 0.6
    spider_meta_timeout_factor = 0.4

    ctx = click.Context(ci_index)
    data = ctx.invoke(ci_index, timeout_minutes=timeout_minutes *
                      spider_index_timeout_factor)

    # data from the index spider
    index_feed = data['feed']
    index_data = data['data*']
    index_data_new = data['data']


    if CI:
        print(f"Using `{index_feed}` {len(index_data)} for meta spider (including new discovered items {len(index_data_new)})")
        # When CI env is set (means it is running on GitHub Actions)
        # On Github Actions, for some reason the multiprocessing does not actually isolate the process, causing `twisted.internet.error.ReactorNotRestartable`
        # Therefore, we have to use subprocess.run() instead of multiprocessing.Process on GitHub Actions (Ubuntu)
        subprocess.run([
            'python',
            'ci.py',
            'meta',
            '--timeout-minutes', str(int(timeout_minutes * spider_meta_timeout_factor)), # todo: update to take floating point
            '--index', index_feed
        ])
    else:
        print(f"Using `data*` {len(index_data)} for meta spider (including new discovered items {len(index_data_new)})")

        # since scrapy does not allow running multiple crawler processes in the same thread,
        # we have to run the meta spider in a separate process
        kwargs = {
            "timeout_minutes": timeout_minutes * spider_meta_timeout_factor,
            "index": index_data,
        }
        p = Process(target=update_meta, kwargs=kwargs)
        p.start()
        p.join()


if __name__ == "__main__":
    cli()
