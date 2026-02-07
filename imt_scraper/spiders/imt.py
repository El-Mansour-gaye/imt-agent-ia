# BRANCH: feature/m1-scraping
import scrapy
from imt_scraper.items import ImtPage
from bs4 import BeautifulSoup
from scrapy.http import TextResponse

class ImtSpider(scrapy.Spider):
    name = "imt"
    allowed_domains = ["www.imt.sn"]
    start_urls = ["https://www.imt.sn/"]

    def parse(self, response):
        # Safety check: ensure response is text/HTML
        if not isinstance(response, TextResponse):
            self.logger.warning(f"Ignored non-text response: {response.url}")
            return

        # Extract item
        item = ImtPage()
        item["url"] = response.url
        item["title"] = response.xpath("//title/text()").get()
        item["content"] = response.body.decode(response.encoding, errors='ignore')
        item["section"] = self.get_section(response.url)
        item["links"] = [response.urljoin(link) for link in response.xpath("//a/@href").getall()]

        yield item

        # Follow all internal links
        ignored_extensions = [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx"]

        for link in response.xpath("//a/@href").getall():
            # Filter to stay on imt.sn and avoid media files
            absolute_url = response.urljoin(link).lower()

            # Extension check
            if any(absolute_url.split('?')[0].endswith(ext) for ext in ignored_extensions):
                continue

            if any(domain in absolute_url for domain in self.allowed_domains):
                yield response.follow(link, self.parse)

    def get_section(self, url):
        parts = url.strip('/').split('/')
        if len(parts) > 3:
            return parts[3]
        return "home"
