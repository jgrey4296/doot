#!/Users/jgrey/anaconda/bin/python
import os
import json

def open_file(filename):
    x = None
    with open("../data/"+filename, 'r') as f:
        x = f.read()
    return x

def readJson(text):
    return json.loads(text)

if __name__ == '__main__':
    print('Starting json opener')
    contents = open_file('Firefox.json')
    jsonContents = readJson(contents)
    print([x for x in jsonContents.keys()])
    
