# BRANCH: feature/m1-scraping
BOT_NAME = "imt_scraper"

SPIDER_MODULES = ["imt_scraper.spiders"]
NEWSPIDER_MODULE = "imt_scraper.spiders"

# Respect robots.txt rules
ROBOTSTXT_OBEY = True

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 1.0

# Configure item pipelines
ITEM_PIPELINES = {
    "imt_scraper.pipelines.ImtCleaningPipeline": 300,
    "imt_scraper.pipelines.JsonWriterPipeline": 400,
}

# Set settings for beautifulsoup
# No specific settings needed here as it will be used in the spider or pipeline

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
