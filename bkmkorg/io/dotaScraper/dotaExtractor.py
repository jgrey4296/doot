from patchNoteExtractor import PatchNoteExtractor
from totalLinkExtractor import DotaLinkExtractor
import time

if __name__ == "__main__":
    totalLinks = []
    count = 0
    #Start here
    fileName = "../htmlData/dota" + str(count) + ".html"
    print("Extracting")
    dle = DotaLinkExtractor("http://dota2.gamepedia.com", "/Category:Patches", fileName)
    data = dle.scrape()
    totalLinks = data['allLinks']

    while data['nextPage']:
        print("Next Page")
        count += 1
        fileName = "../htmlData/dota" + str(count) + ".html"
        dle = DotaLinkExtractor("http://dota2.gamepedia.com", 
                                data['nextPage'], 
                                fileName)
        data = dle.scrape()
        totalLinks += data['allLinks']

    #all the patch note links:
    print("Data Extracted: ", len(totalLinks))


    #Now for each patch note:
    patchNoteInformation = {}
    fileName = "../htmlData/dotaPatchNote"


    for x in totalLinks:
        dle = PatchNoteExtractor("http://dota2.gamepedia.com", x, fileName)
        patchNoteInformation[x], readFile = dle.scrape()
        if not readFile:
            time.sleep(60)

    for x in patchNoteInformation.keys():
        print(x)
        for y in patchNoteInformation[x].keys():
            print(y)
            print(patchNoteInformation[x][y])
