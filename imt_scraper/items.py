# BRANCH: feature/m1-scraping
import scrapy

class ImtPage(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    content = scrapy.Field()
    section = scrapy.Field()
    links = scrapy.Field()
