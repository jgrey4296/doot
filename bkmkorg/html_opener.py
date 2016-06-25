#!/Users/jgrey/anaconda/bin/python
import os
from bs4 import BeautifulSoup
from json_opener import open_file
import util




if __name__ == '__main__':
    print('Opening html');
    rawHtml = open_file('Safari.html')
    print(rawHtml[0:10])
