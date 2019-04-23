import logging as root_logger
logging = root_logger.getLogger(__name__)
from bs4 import BeautifulSoup
from bs4.element import NavigableString
import IPython

def parseData(s):
    assert(isinstance(s, str))
    logging.info("Initiating data parse")
    data = {}
    soup = BeautifulSoup(s, "lxml")

    for x,y in get_darktable(soup):
        if '\n' in y:
            y = y.split('\n')
        if isinstance(y, list) and len(y) == 1:
            y = y[0]
        data[x] = y
    
    for x,y in get_main_data(soup):
        if '\n' in y:
            y = y.split('\n')
        if isinstance(y, list) and len(y) == 1:
            y = y[0]
        data[x] = y
        
    return data


def get_darktable(soup):
    tables = [x for x in soup.find(id='mw-content-text').find_all('table') if x.has_attr('class') and 'darktable' in  x['class']]
    if len(tables) > 1:
        logging.warning("More than one dark table")
    elif len(tables) == 0:
        return []
        
    pairings = []
    
    table_data = tables[0]
    elements = table_data.find_all('tr')
    title = elements[0].find_all('span')[1].get_text()
    pairings.append(('title', title))
    
    rest = elements[1:]
    for r in rest:
        pairs = r.find_all('td')
        if len(pairs) < 2:
            continue
        try:
            lcol = pairs[0].get_text().strip()
        except IndexError:
            IPython.embed(simple_prompt=True)
        #reputation special case
        if lcol == 'Reputation':
            rcol = parse_reputation(pairs[1])
        else:
            try:
                pairs[1]
            except IndexError:
                IPython.embed(simple_prompt=True)
            if len(list(pairs[1].children)) > 1:
                rcol = []
                for c in pairs[1].children:
                    if hasattr(c, 'get_text'):
                        rcol.append(c.get_text().strip())
                    elif isinstance(c, NavigableString):
                        rcol.append(str(c).strip())
                rcol = " ".join(rcol).split("\n")
            else:
                rcol = pairs[1].get_text().strip().split("\n")
                
        pairings.append((lcol, rcol))
        
    return pairings

def parse_reputation(soup):
    contents = list(soup.stripped_strings)
    filtered = [x for x in contents if x != ':' and x != '/']
    if len(filtered) % 2 != 0:
        return filtered
    paired = list(zip(filtered[::2], filtered[1::2]))
    if len(paired) < 6:
        return [" ".join(x) for x in paired]
    indices = [i for i,x in enumerate(paired) if x[1] == 'Alliance' or x[1] == 'Horde']
    try:
        assert(len(indices) == 2)
    except AssertionError:
        logging.info("Parse reputation issue")
        IPython.embed(simple_prompt=True)
    output = { "alliance" : {"value": 0, "subgroups" : {} },
               "horde" : {"value": 0, "subgroups" : {} } }
    output['alliance']['value'] = paired[indices[0]][0]
    output['horde']['value'] = paired[indices[1]][0]
    output['alliance']['subgroups'] = {x:y for x,y in paired[1:indices[1]]}
    output['horde']['subgroups'] = {x:y for x,y in paired[indices[1]+1:]}
    return output
    


def get_main_data(soup):
    main = soup.find(id='mw-content-text')
    #Get the main group headers
    headlines = [(x.parent, x.get_text().strip()) for x in main.find_all(class_='mw-headline')]
    #Detect the last one
    if len(headlines) == 0:
        return []
    if headlines[-1][1] != 'External links':
        logging.warning('Last header is: {}'.format(headlines[-1][1]))
        
    #lop off the last as its not usually important
    #headlines = headlines[:-1]
    assert(all(['h' in x[0].name for x in headlines]))

    #aggregate the information:
    try:
        start = headlines[0]
    except IndexError:
        IPython.embed(simple_prompt=True)
    if not start[1] == 'Objectives':
        logging.warning("Headlines don't start with objectives: {}".format(start[1]))
        
    segments = []
    collected = []

    #Loop from the first header until the footer
    current = start[0].next_sibling
    while current is not None and not ('class' in current and current['class'] == 'printfooter'):
        #skip over if you hit the external links
        if hasattr(current, 'get_text') and 'External links' in current.get_text():
            break
        #if you hit a table, ignore it
        if current.name == 'table' or current.name is None:
            current = current.next_sibling
            continue
        #when you hit a header, move to a new segment
        if hasattr(current, 'name') and 'h' in current.name:
            segments.append(collected)
            collected = []
        elif (isinstance(current, NavigableString) and len(current.strip()) > 0):
            IPython.embed(simple_prompt=True)
            text = str(current).strip()
            if '\n' in text:
                text = text.split('\n')
            collected.append(str(current).strip())
        elif not isinstance(current, NavigableString):
            text = current.get_text().strip()
            potential_img = current.find('img')
            if bool(potential_img) and potential_img.has_attr('alt'):
                text += " " + potential_img['alt']
            if '\n' in text:
                text = text.split('\n')
            collected.append(text)
        current = current.next_sibling
    if len(collected) > 0:
        segments.append(collected)
    if len(headlines) != len(segments):
        logging.warning("Headlines and segments don't match")
    headline_titles = [x[1] for x in headlines]
    return zip(headline_titles, segments)
                         
    
