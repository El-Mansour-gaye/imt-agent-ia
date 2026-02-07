# BRANCH: feature/m1-scraping
import scrapy
from imt_scraper.items import ImtPage
from bs4 import BeautifulSoup
from scrapy.http import TextResponse

class ImtSpider(scrapy.Spider):
    name = "imt"
    allowed_domains = ["imt.sn", "www.imt.sn"]
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

        # Clean text extraction with BeautifulSoup
        soup = BeautifulSoup(response.body, "html.parser")
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # Get text, joining with spaces and cleaning up whitespace
        clean_text = soup.get_text(separator=" ")
        lines = (line.strip() for line in clean_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        item["content"] = "\n".join(chunk for chunk in chunks if chunk)

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
