#!/usr/bin/env python
# -*- coding: utf-8 -*-
#find unique users
import xml.etree.cElementTree as ET
import pprint
import re
"""
Your task is to explore the data a bit more.
The first task is a fun one - find out how many unique users
have contributed to the map in this particular area!

The function process_map should return a set of unique user IDs ("uid")
"""

def get_user(element):
    return


def process_map(filename):
    users = set()
    for _, element in ET.iterparse(filename):
        if element.tag=='node' or element.tag=='way':
            if element.attrib['uid'] not in users:
                users.add(element.attrib['uid'])
       

    return users


def test():

    users = process_map('sample1.osm')
    pprint.pprint(users)
    print len(users)



if __name__ == "__main__":
    test()