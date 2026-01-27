# BRANCH: feature/m1-scraping
import scrapy
from imt_scraper.items import ImtPage
from bs4 import BeautifulSoup

class ImtSpider(scrapy.Spider):
    name = "imt"
    allowed_domains = ["www.imt.sn"]
    start_urls = ["https://www.imt.sn/"]

    def parse(self, response):
        # Extract item
        item = ImtPage()
        item["url"] = response.url
        item["title"] = response.xpath("//title/text()").get()
        item["content"] = response.body.decode(response.encoding, errors='ignore')
        item["section"] = self.get_section(response.url)
        item["links"] = [response.urljoin(link) for link in response.xpath("//a/@href").getall()]

        yield item

        # Follow all internal links
        for link in response.xpath("//a/@href").getall():
            # Filter to stay on imt.sn
            absolute_url = response.urljoin(link)
            if any(domain in absolute_url for domain in self.allowed_domains):
                yield response.follow(link, self.parse)

    def get_section(self, url):
        parts = url.strip('/').split('/')
        if len(parts) > 3:
            return parts[3]
        return "home"
