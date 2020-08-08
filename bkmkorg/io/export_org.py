"""
A org exporter for bookmarks
"""
import logging as root_logger
logging = root_logger.getLogger(__name__)

TAG_COL = 80

def tuple_to_str(bkmk_tuple):
    fixed_name = bkmk_tuple.name.replace('[', '(').replace(']', ')')
    headline_link = "** [[{}][{}...]]".format(bkmk_tuple.url,
                                              fixed_name[:40])
    head_len = len("** {}...".format(bkmk_tuple.name[:40]))
    offset = 80 - head_len

    return "{}{}:{}:\n{}\n".format(headline_link,
                                   " " * offset,
                                   ":".join(bkmk_tuple.tags),
                                   bkmk_tuple.name)


def exportBookmarks(data, filename):
    """ Main function. Takes a dict of data and outputs a string """
    #print out the items that are bookmark tuples
    logging.info("Converting data to text")
    target_data = None
    if isinstance(data, dict):
        target_data = data.values()
    else:
        target_data = data
    with open(filename, 'w') as f:
        for x in target_data:
            theString = tuple_to_str(x) + "\n"
            f.write(theString)
