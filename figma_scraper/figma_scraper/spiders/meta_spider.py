import json
import jsonlines
import scrapy
import scrapy.http
from tqdm import tqdm


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

        self.progress_bar = tqdm(
            total=len(self.start_urls), position=0)

    def parse(self, response: scrapy.http.Response):
        di = response.xpath('//script/@data-initial')
        text = di.get()
        data = parse_from_next_script_props(text)

        self.progress_bar.update(1)
        tqdm.write(f"☑ {response.url}")

        yield data
