from __future__ import annotations


class ScrapyScraperAPIMiddleware:
    """This middleware applies your ScraperAPI settings to be used as a proxy"""

    def __init__(self, settings) -> None:
        self.key = settings.get('SCRAPERAPI_KEY')
        self.user = self.__get_user(settings.get('SCRAPERAPI_OPTIONS'))

    @classmethod
    def from_crawler(cls, crawler) -> ScrapyScraperAPIMiddleware:
        return cls(crawler.settings)

    def __get_user(self, options) -> str:
        # the username is always scraperapi
        user = 'scraperapi'
        # if there are options, they need to be added to the username
        if options is not None and isinstance(options, dict):
            for key, value in options.items():
                user = f'{user}.{key}={value}'
        return user

    def process_request(self, request, spider) -> None:
        request.meta['proxy'] = f'http://{self.user}:{self.key}@proxy-server.scraperapi.com:8001'
