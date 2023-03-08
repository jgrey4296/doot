"""
# template settings for spiders
[spiders.general]
# DUPEFILTER_DEBUG                     = true
JOBDIR                               = ".temp"
FEED_TEMPDIR                         = ".temp"
#LOG_FORMAT                          = ""
# LOG_FILE                             = "scrapy.log"
# disable_existing_loggers = false
# LOG_LEVEL                            = "DEBUG"
# LOG_STDOUT                           = false
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR                      = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING                 = "utf-8"
USER_AGENT                           = "Scrapy/VERSION (+https://scrapy.org)"
DEPTH_LIMIT                          = 1
CONCURRENT_REQUESTS                  = 16
DOWNLOAD_DELAY                       = 3
DOWNLOAD_TIMEOUT                     = 100
# ROBOTSTXT_OBEY                     = true
#DOWNLOAD_WARNSIZE                   = 33554432
#DOWNLOAD_MAXSIZE                    = 1073741824
#COOKIES_ENABLED                     = false
TELNETCONSOLE_ENABLED                = false

[spiders.throttle]
#AUTOTHROTTLE_ENABLED                = True
#AUTOTHROTTLE_START_DELAY            = 5
#AUTOTHROTTLE_MAX_DELAY              = 60
#AUTOTHROTTLE_TARGET_CONCURRENCY     = 1.0
#AUTOTHROTTLE_DEBUG                  = False

[spiders.caching]
HTTPCACHE_DIR                 = ".temp/cache"
HTTPCACHE_ENABLED             = true
HTTPCACHE_EXPIRATION_SECS     = 0
HTTPCACHE_STORAGE             = "doot.spiders.caching.CacheStorage"
HTTPCACHE_POLICY              = "doot.spiders.caching.CachePolicy"
# HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_GZIP                = true

[spiders.pipeline]
# DEFAULT_REQUEST_HEADERS = { "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language"= "en" }
# SPIDER_MIDDLEWARES      = { "doot.spiders.middleware.SpiderMiddleware"     = 543 }
# DOWNLOADER_MIDDLEWARES  = { "doot.spiders.middleware.DownloaderMiddleware" = 543 }
# DOWNLOAD_HANDLERS       = {}
EXTENSIONS                = { "scrapy.extensions.telnet.TelnetConsole"            = false }
# ITEM_PIPELINES          = { "doot.spiders.pipeline.ItemPipeline"  = 300, "doot.spiders.pipeline.SimpleExporter" = 1000 }
"""
