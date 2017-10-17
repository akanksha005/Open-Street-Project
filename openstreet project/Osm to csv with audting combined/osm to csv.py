#!/usr/bin/env python
# -*- coding: utf-8 -*-

#convert Osm file into respective csvs with auditing of the dataset

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
from collections import defaultdict
import cerberus

import schema

OSM_PATH = "sample1.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
postal_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
zip_code_re = re.compile(r'^\d{4}$')
fix_zipcode_state_short = re.compile(r'\d{4};\d{4}$')

expected = ["St","St.","Rd.","Av","Gr",'Stg',"Rd"]

# UPDATE THIS VARIABLE
mapping = { "St": "Street",
            "St.": "Street",
            "Rd.":"Road",
            "Av":"Avenue",
           "Gr":'Grove',
           'Stg':"Street"
            }


def audit_street_type(street_types, street_name):
    abbr=False
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type in expected:
            abbr=True
            street_types[street_type].add(street_name)
def audit_postal_type(postal_types, postal_name):
    m = postal_type_re.search(postal_name)
    if m:
        postal_type = m.group()
        if len(postal_type)>4 or len(postal_type)<4:
            postal_types[postal_type].add(postal_name)

def audit_zip_code(zip_code):
    change=False
    new_code=zip_code
    zip_code = zip_code.strip()
    
    m = zip_code_re.search(zip_code)
    if zip_code[4:9] == 'Unset':
        change=True
        new_code = zip_code[0:4]
        return change,new_code,zip_code
    if fix_zipcode_state_short.search(zip_code):
        change=True
        new_code = zip_code[0:4]
        return change,new_code,zip_code
    if m:
        return change,new_code,zip_code
    if zip_code=='':
        return True,"none","none"
    else:
        return change,new_code,zip_code

def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")
def is_postal_name(elem):
    return (elem.attrib['k'] == "addr:postcode")

def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
                    if(abbr):
                        tag.attrib['v']=update_name( tag.attrib['v'], mapping)
                    c,n,code=audit_zip_code(tag.attrib['v'])
                if is_postal_name(tag):
                    audit_postal_type(postal_types, tag.attrib['v'])
                    c,n,code=audit_zip_code(tag.attrib['v'])
                    if c:
                        tag.attrib['v'] = n
    osm_file.close()
    return street_types


def update_name(name, mapping):
    m = street_type_re.search(name)
    for key,value in (mapping).iteritems():
        if key==m.group():
           name=name.replace(key,value)
        

    return name


def test():
    st_types = audit(OSMFILE)
    
    pprint.pprint(dict(st_types))

    for st_type, ways in st_types.iteritems():
        for name in ways:
            better_name = update_name(name, mapping)
            print name, "=>", better_name

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,NODE_TAGS_FIELDS=NODE_TAGS_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    
   
    if element.tag == 'node':
        for i in node_attr_fields:
            node_attribs[i]=element.attrib[i]
        
        for tag in element:
            nodes={}
            if problem_chars.match(tag.attrib['k']):
                pass
            elif LOWER_COLON.match(tag.attrib['k']):
                nodes['id']=element.attrib['id']
                nodes['key']=tag.attrib['k'].split(":",1)[1]
                nodes['type']=tag.attrib['k'].split(":",1)[0]
                nodes['value']=tag.attrib['v']
            else:
                nodes['id']=element.attrib['id']
                nodes['key']=tag.attrib['k']
                nodes['type']='regular'
                nodes['value']=tag.attrib['v']
            tags.append(nodes)
        
        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        for i in way_attr_fields:
            way_attribs[i]=element.attrib[i]
            position=0
        for child in element:
            way_n = {}
            way_t = {}
            if child.tag == "nd":
                if element.attrib["id"] not in way_nodes:
                    way_n["position"] = position
                    way_n["id"] = element.attrib["id"]
                    way_n["node_id"] = child.attrib["ref"]
                    way_nodes.append(way_n)
                    position += 1
                else:
                    way_n["position"] += 1
                    way_n["id"] = element.attrib["id"]
                    way_n["node_id"] = child.attrib["ref"]
                    way_nodes.append(way_n)
            elif child.tag == "tag":
                if PROBLEMCHARS.match(child.attrib["k"]):
                    pass
                elif LOWER_COLON.match(child.attrib["k"]):
                    way_t["type"] = child.attrib["k"].split(":",1)[0]
                    way_t["key"] = child.attrib["k"].split(":",1)[1]
                    way_t["id"] = element.attrib["id"]
                    way_t["value"] = child.attrib["v"]
                    tags.append(way_t)
                else:
                    way_t["type"] = "regular"
                    way_t["key"] = child.attrib["k"]
                    way_t["id"] = element.attrib["id"]
                    way_t["value"] = child.attrib["v"]
                    tags.append(way_t)
                    
        print way_nodes
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    test()
    process_map(OSM_PATH, validate=True)
