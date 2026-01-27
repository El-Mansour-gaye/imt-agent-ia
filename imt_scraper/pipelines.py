# BRANCH: feature/m1-scraping
import json
import scrapy
from bs4 import BeautifulSoup
from itemadapter import ItemAdapter

class ImtCleaningPipeline:
    def __init__(self):
        self.urls_seen = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Deduplication
        url = adapter.get("url")
        if url in self.urls_seen:
            raise scrapy.exceptions.DropItem(f"Duplicate item found: {url}")
        self.urls_seen.add(url)

        # BeautifulSoup cleaning
        html_content = adapter.get("content")
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # Extract title, h1-h3, and p
        texts = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
            text = tag.get_text(strip=True)
            if text:
                texts.append(text)

        adapter["content"] = "\n".join(texts)

        # Clean links (already absolute from spider)
        links = adapter.get("links")
        clean_links = []
        for link in links:
            if link and not link.startswith(("#", "mailto:", "tel:")):
                clean_links.append(link)
        adapter["links"] = list(set(clean_links))

        return item

class JsonWriterPipeline:
    def open_spider(self, spider):
        self.file = open("imt_data.json", "w", encoding="utf-8")
        self.items = []

    def close_spider(self, spider):
        json.dump(self.items, self.file, ensure_ascii=False, indent=2)
        self.file.close()

    def process_item(self, item, spider):
        self.items.append(ItemAdapter(item).asdict())
        return item
