import json
import os
import jsonlines
import scrapy
import scrapy.http
from tqdm import tqdm


class FigmaMetaSpider(scrapy.Spider):
    name = 'meta_spider'
    start_urls = []
    progress_bar: tqdm

    def __init__(self, index, **kwargs):
        max = kwargs.pop('max', None)
        proxy = kwargs.pop('proxy', False)

        # read the index file, seed the start_urls
        if type(index) == str:
            with jsonlines.open(index) as reader:
                self.start_urls = [x['link'] for x in reader]
        # also accepts the data parsed from the index file externally
        elif type(index) == list:
            self.start_urls = [x['link'] for x in index]
        else:
            raise Exception(
                'index must be a path to a jsonl file or a list of objects')

        if max:
            self.start_urls = self.start_urls[:int(max)]

        if proxy:
            # ensure api key provided
            SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")
            if not SCRAPERAPI_KEY:
                raise Exception(
                    'SCRAPERAPI_KEY must be provided when using proxy')

            self.custom_settings = {
                # scraperapi settings
                "SCRAPERAPI_KEY": SCRAPERAPI_KEY,
                "SCRAPERAPI_OPTIONS": {
                    'render': 'false',
                    'country_code': 'us'
                },

                'DOWNLOADER_MIDDLEWARES': {
                    'figma_scraper.middlewares.scraperapi.ScrapyScraperAPIMiddleware': 350,
                    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 400,
                }
            }

        # index_name = Path(index).stem
        # output = Path(f'./data/{index_name}.meta.json')
        # create the output file if it doesn't exist
        # output.touch(exist_ok=True)

        # override the FEED_URI
        # self.custom_settings = {
        #     'FEED_URI': output,
        #     'FEED_FORMAT': 'json',
        #     'FEED_EXPORT_ENCODING': 'utf-8',
        #     'FEED_EXPORT_BATCH_ITEM_COUNT': 1,
        # }

        self.progress_bar = tqdm(
            total=len(self.start_urls), position=0)

    def parse(self, response: scrapy.http.Response):
        di = response.xpath('//script/@data-initial')
        text = di.get()
        data = json.loads(text)

        INITIAL_OPTIONS = data['INITIAL_OPTIONS']
        print(json.dumps(INITIAL_OPTIONS))
        community_preloads = INITIAL_OPTIONS['community_preloads']
        hub_file = community_preloads['hub_file']
        hub_file_publisher = hub_file['publisher']
        versions = hub_file['versions']

        # find the latest version with entry[key].created_at, where versions is a key:value dict
        latest_version_id = max(
            versions, key=lambda key: versions[key]['created_at'])
        latest_version = versions[latest_version_id]

        version_id = latest_version_id
        version = latest_version['version']  # 1, 2, 3, etc
        name = latest_version['name']
        description = latest_version['description']  # html long description

        # the "see also" field
        related_content__original = hub_file['related_content']
        # minify 'content' field by extracting onlu ids (it's a list of object containg details -> list of ids)
        related_content_content = [x['id']
                                   for x in related_content__original['content']]

        related_content = {
            'content': related_content_content,
            'types': related_content__original['types'],
        }

        # list of co-publishers id
        community_publishers = [x['id']
                                for x in hub_file['community_publishers']['accepted']]

        data = {
            'id': hub_file['id'],
            'name': name,
            'description': description,
            'version_id': version_id,
            'version': version,
            'created_at': hub_file['created_at'],
            'duplicate_count':  hub_file['duplicate_count'],
            'like_count': hub_file['like_count'],
            'thumbnail_url': hub_file['thumbnail_url'],
            'redirect_canvas_url': hub_file['redirect_canvas_url'],
            'community_publishers': community_publishers,
            'publisher': {
                'id': hub_file_publisher['id'],
                'profile_handle': hub_file_publisher['profile_handle'],
                'follower_count': hub_file_publisher['follower_count'],
                'following_count': hub_file_publisher['following_count'],
                'primary_user_id': hub_file_publisher['primary_user_id'],
                'name': hub_file_publisher['name'],
                'img_url': hub_file_publisher['img_url'],
                'badges': hub_file_publisher['badges'],
            },
            'support_contact': hub_file['support_contact'],
            'creator': hub_file['creator'],
            'tags': hub_file['tags'],
            'badges': hub_file['badges'],
            'related_content': related_content,
        }

        self.progress_bar.update(1)
        tqdm.write(f"☑ {response.url}")

        yield data
