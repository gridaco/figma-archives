import json
import os
import time
import jsonlines
import scrapy
import scrapy.http
from scrapy.selector import Selector
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from pyvirtualdisplay import Display


def parse_from_next_script_props(text):
    data = json.loads(text)

    D = data['INITIAL_OPTIONS']
    hub_file = D['hub_file']
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
        # related content is no longer present in the response
        'related_content': {},
    }

    # related content is no longer present in the response
    # # the "see also" field
    # related_content__original = hub_file['related_content']
    # # minify 'content' field by extracting onlu ids (it's a list of object containg details -> list of ids)
    # related_content_content = [x['id']
    #                             for x in related_content__original['content']]
    # related_content = {
    #     'content': related_content_content,
    #     'types': related_content__original['types'],
    # }

    return data


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
                ids = [x['id'] for x in reader]
        # also accepts the data parsed from the index file externally
        elif type(index) == list:
            ids = [x['id'] for x in index]
        else:
            raise Exception(
                'index must be a path to a jsonl file or a list of objects')

        # e.g. https://embed.figma.com/file/1035203688168086460/hf_embed?community_viewer=true&embed_host=hub_file_detail_view&hide_ui=true&hub_file_id=1035203688168086460&kind=&viewer=1
        # we use embed.figma.com url since there the url provides the metadata in next script tag
        self.start_urls = [
            f"https://embed.figma.com/file/{id}/hf_embed?community_viewer=true&embed_host=hub_file_detail_view&hide_ui=true&hub_file_id={id}&kind=&viewer=1" for id in ids]

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


        CI = os.getenv("CI")
        # setup selenium
        options = Options()

        if CI:
            # this spider crawls figma embed page, which requires a webgl enabled browser, won't work if headless mode.
            # you can set size to whatever you like
            display = Display(visible=0, size=(800, 600))
            display.start()
        else:
            ...

        self.driver = webdriver.Chrome(service=Service(
            executable_path=ChromeDriverManager().install()), options=options)
        # wait extra to ensure the page is loaded

        self.progress_bar = tqdm(
            total=len(self.start_urls), position=0)

    def start_requests(self):
        for url in self.start_urls:
            print(url)
            self.driver.get(url)
            # wait for the page to load
            # check if div with id 'react-page' is present
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "react-page")))

            body = self.driver.page_source
            yield scrapy.Request(url, self.parse, dont_filter=True, meta={'body': body})

    def parse(self, response: scrapy.http.Response):
        body = response.meta['body']
        selector = Selector(text=body)
        di = selector.xpath('//script/@data-initial')
        text = di.get()
        data = parse_from_next_script_props(text)

        self.progress_bar.update(1)
        tqdm.write(f"☑ {response.url}")

        yield data

    def close(self, reason):
        self.driver.close()
