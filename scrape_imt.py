# BRANCH: feature/m1-scraping
import os
import sys
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from imt_scraper.spiders.imt import ImtSpider

def run_spider():
    # Set the environment variable for scrapy settings
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'imt_scraper.settings')

    process = CrawlerProcess(get_project_settings())
    process.crawl(ImtSpider)
    process.start()

    if os.path.exists("imt_data.json"):
        print(f"Successfully crawled and saved data to imt_data.json")
    else:
        print("Crawl failed or imt_data.json was not created.")

if __name__ == "__main__":
    run_spider()
