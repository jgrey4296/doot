# @module totalLinkExtractor
from __future__ import print_function
from __future__ import unicode_literals
from cookielib import CookieJar
import re
import urllib2
import urllib
from bs4 import BeautifulSoup
import json
import logging
import os
from datetime import datetime

class DotaLinkExtractor:

    #the creation myth:
    def __init__(self, siteUrl, pageUrl, filename):
        logging.info("Initialising dota link extractor for:",
                     siteUrl, pageUrl, filename)
        self.siteUrl = siteUrl
        self.url = siteUrl + pageUrl
        self.options = ""
        self.filename = filename

        cj = CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        self.html = ""


    #Main Trigger Method, returns the information extracted
    #method scrape
    def scrape(self, url=None):
        if url is None:
            url = self.url

        #the object that will hold the information
        extractedInfo = []

        #get the html
        self.html = self.webRequest(url)
        #extract information
        extractedInfo = self.informationExtraction(self.html)

        logging.info( "Extracted Profile Info")#, extractedInfo
        return extractedInfo

    #Get a url, with any post values to add
    def webRequest(self, url):
        header = { 'User-Agent':"Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7" }

        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                self.html = f.read()
            print("Skipped html request, file already exists")
            return self.html

        #encode the values into a url form
        data = urllib.urlencode(self.options)
        #package the url and values together
        print("Retrieving: ", url, data)
        request = urllib2.Request(url, data, header)
        #get the information
        self.response = self.opener.open(request)
        #read the information
        self.html = self.response.read()

        #write the file
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                f.write(self.html)

        return self.html

    #html in -> usable information out
    def informationExtraction(self, html):
        logging.info("Extracting from Profile")
        soup = BeautifulSoup(html)
        #information that is extracted:
        allLinks = []

        #ask questions, get answers
        mainContent = soup.find(id="content").find(id="mw-pages")
        #See if theres more pages
        if mainContent.find(text="next 200"):
            nextTag = mainContent.find(text="next 200").parent
            if nextTag['href']:
                nextPageUrl = nextTag['href']
            else:
                nextPageUrl = None
        else:
            nextPageUrl = None

        #get the actual patch links:
        for x in mainContent.find_all("a"):
            name = x['title']
            try:
                date = datetime.strptime(name, "%B %d, %Y Patch")
                allLinks.append(x['href'])
            except Exception as e:
                1 + 1
                #print("Error for: ", name, e)


        return {
            "allLinks": allLinks,
            "nextPage" : nextPageUrl
            }

#Example usage
if __name__ == "__main__":
    totalLinks = []
    count = 0
    fileName = "../htmlData/dota" + str(count) + ".html"
    print("Extracting")
    dle = DotaLinkExtractor("http://dota2.gamepedia.com",
                            "/Category:Patches",
                            fileName)
    data = dle.scrape()
    totalLinks = data['allLinks']

    while data['nextPage']:
        print("Next Page")
        count += 1
        fileName = "../htmlData/dota" + str(count) + ".html"
        dle = DotaLinkExtractor("http://dota2.gamepedia.com",
                                data['nextPage'], fileName)
        data = dle.scrape()
        totalLinks += data['allLinks']


    print("Data Extracted: ", totalLinks, count)
