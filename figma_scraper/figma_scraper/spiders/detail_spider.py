import json
import scrapy
from scrapy.selector import Selector
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm

class FigmaSpider(scrapy.Spider):
  name = 'detail_spider'
  start_urls = []
  progress_bar = tqdm(total=1, desc="Collecting Details", position=0)


  def __init__(self, index, **kwargs):
    # read the index file, seed the start_urls
    with open(index, "r", encoding="utf-8") as f:
      index_data = json.load(f)
      self.start_urls = [x['link'] for x in index_data]
      f.close()

    self.progress_bar.total = len(self.start_urls)


  def parse(self, response):
    scrapy_selector = Selector(text=response)
    di = scrapy_selector.xpath('//script/@data-initial')
    text = di.get()
    data = json.loads(text)


    INITIAL_OPTIONS = data['INITIAL_OPTIONS']
    community_preloads = INITIAL_OPTIONS['community_preloads']
    hub_file = community_preloads['hub_file']
    hub_file_publisher = hub_file['publisher']
    versions = hub_file['versions']


    # find the latest version with entry[key].created_at, where versions is a key:value dict
    latest_version_id = max(versions, key=lambda key: versions[key]['created_at'])
    latest_version = versions[latest_version_id]

    version_id = latest_version_id
    version = latest_version['version'] # 1, 2, 3, etc
    name = latest_version['name']
    description = latest_version['description'] # html long description

    related_content__original = hub_file['related_content'] # the "see also" field
    # minify 'content' field by extracting onlu ids (it's a list of object containg details -> list of ids)
    related_content_content = [x['id'] for x in related_content__original['content']]

    related_content = {
        'content': related_content_content,
        'types': related_content__original['types'],
    }

    # list of co-publishers id
    community_publishers = [x['id'] for x in hub_file['community_publishers']['accepted']]

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

    yield data
 