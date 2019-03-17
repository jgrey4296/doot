# Bookmark organiser

To deal with the unmanageable morass of bookmarks I collect.
Safari, Firefox, and Chrome export html bookmarks in the 
[Netscape bookmark file format](https://msdn.microsoft.com/en-us/library/aa753582(v=vs.85).aspx).

## Trie Aggregator

Trie-aggregator loads those bookmark backups in, **ignoring** groups
but **preserving** tags, stores them in a trie based on the bookmarks
url path, removes duplicates, then collapses trie paths that have only
a single child. This collapsed trie is then exported out as the file
'simplified_bookmarks.html' for reloading into Firefox/Chrome/Safari.

### Usage

Create the directory ./raw_bookmarks, and fill it with the html files exported
from your browsers.

run *python trie-aggregator.py*

Reload the simplified bookmarks back into your browser.

## bkmkorg package
This package contains utilities to read and save netscape format bookmark files.
It also has bookmark_simplification to convert loaded bookmarks into a trie.

## Dependencies
** Python 3.5 ** (may work on any python3+, untested)
IPython, BeautifulSoup, and other std library python (re, namedtuples...)


## TODO
Add more comments and test
