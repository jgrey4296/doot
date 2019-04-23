""" Initial patch node extractor
 takes a url in two parts, and extracts
 the patch note information
 @module totalLinkExtractor
"""

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


class PatchNoteExtractor:

    def __init__(self, siteUrl, pageUrl, filename):
        logging.info("Initialising patch note extractor for:", siteUrl, pageUrl, filename)
        self.siteUrl = siteUrl
        self.url = siteUrl + pageUrl
        self.options = ""
        self.filename = filename + pageUrl.replace("/", "") + ".html"

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

        #if the file has already been downloaded
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                self.html = f.read()
            print("Skipped html request, file already exists")
            self.readFile = True
        else:
            self.readFile = False
            #get the html
            self.html = self.webRequest(url)
        #extract information
        extractedInfo = self.informationExtraction(self.html)

        logging.info( "Extracted Profile Info")#, extractedInfo
        return (extractedInfo, self.readFile)

    #Get a url, with any post values to add
    def webRequest(self, url):
        header = { 'User-Agent':"Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7" }

        #encode the values into a url form
        data = urllib.urlencode(self.options)
        #package the url and values together
        print("Retrieving: ", url, data)
        request = urllib2.Request(url, data, header)
        #get the information
        self.response = self.opener.open(request)
        #read the information
        self.html = self.response.read()

        #write the file if it doesnt exist
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                f.write(self.html)

        return self.html

    #html in -> usable information out
    def informationExtraction(self, html):
        logging.info("Extracting from Profile")
        soup = BeautifulSoup(html)
        #information that is extracted:
        patch_note = {}


        toc = soup.find(id="content").find(id="mw-content-text").find_all("h2")

        #For everything found after the toc
        for x in toc:
            if x.next_sibling == None or  x.next_sibling.next_sibling == None:
                continue

            allEntries = x.next_sibling.next_sibling.find_all("li")
            if len(allEntries) > 0:
                #store the array of list items it has
                patch_note[x.text] = [y.text for y in allEntries]

        #return the patch notes
        return patch_note

#example usage
if __name__ == "__main__":
    name = "/August_28, _2013_Patch"
    fileName = "../htmlData/dotaPatchNote"
    print("Extracting")
    dle = PatchNoteExtractor("http://dota2.gamepedia.com", name, fileName)
    data = dle.scrape()

    for x in data.keys():
        print("\n\nKEY: ", x)
        print(data[x])
