import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint

OSMFILE = "sample.osm"
postal_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
zip_code_re = re.compile(r'^\d{4}$')
fix_zipcode_state_short = re.compile(r'\d{4};\d{4}$')


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


def is_postal_name(elem):
    return (elem.attrib['k'] == "addr:postcode")


def audit(osmfile):
    osm_file = open(osmfile, "r")
    postal_types = defaultdict(set)
    print "After Auditing:"
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_postal_name(tag):
                    audit_postal_type(postal_types, tag.attrib['v'])
                    c,n,code=audit_zip_code(tag.attrib['v'])
                    if c:
                       
                        print str(tag.attrib['v']) +"=>"+str(n)
    osm_file.close()
    return postal_types



def test():
    postal_types = audit(OSMFILE)
    print "\n"
    print "Inconsistent Postal Codes:"
    pprint.pprint(dict(postal_types))

if __name__ == '__main__':
    test()