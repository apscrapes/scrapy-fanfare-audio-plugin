import scrapy


class BrokenSpider(scrapy.Spider):
    """Demo spider that scrapes nothing — triggers the failure beep."""

    name = "broken"
    start_urls = ["http://localhost:1/"]

    def parse(self, response):
        yield {"data": response.text}
