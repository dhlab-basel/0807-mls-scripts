import argparse
from pprint import pprint
from knora import KnoraError, knora, BulkImport
from xml.dom.minidom import parse
import xml.dom.minidom
import json
import requests

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--server", type=str, default="http://0.0.0.0:3333", help="URL of the Knora server")
parser.add_argument("-u", "--user", type=str, default="root@example.com", help="Username for Knora")
parser.add_argument("-p", "--password", type=str, default="test", help="The password for login")
parser.add_argument("-P", "--projectcode", type=str, default="0807", help="Project short code")
parser.add_argument("-O", "--ontoname", type=str, default="mls", help="Shortname of ontology")
parser.add_argument("-x", "--xml", type=str, default="mls-bulk.xml", help="Name of bulk import XML-File")
parser.add_argument("--start", default="1", help="Start with given line")
parser.add_argument("--stop", default="all", help="End with given line ('all' reads all lines")

args = parser.parse_args()

con = knora(args.server, args.user, args.password)
schema = con.create_schema(args.projectcode, args.ontoname)

sex_lut = {
    'männlich': 'male',
    'weiblich': 'female',
    'weiblich & männliche Gruppe': 'male+female'
}

article_type_lut = {
    'Person': 'person',
    'Sache': 'thing',
    'Ort': 'location',
    'Institution': 'institution',
    'Liste': 'List'
}


# load the lists.json file
with open("lists.json", "r") as lists_file:
    lists = json.load(lists_file)


def get_list_iri(listname):
    return lists[listname]["id"]


def get_list_node_iri(listname, nodename):
    nodes = lists[listname]["nodes"]
    res = ""
    for node in nodes:
        try:
            res = node[nodename]["id"]
        except KeyError:
            pass

    if res == "":
        return None
    else:
        return res


def get_valpos(xmlfile):
    DOMTree = xml.dom.minidom.parse(xmlfile)
    collection = DOMTree.documentElement
    fields = collection.getElementsByTagName("FIELD")

    valpos = []
    for field in fields:
        name = field.getAttribute('NAME')
        valpos.append(name)

    pprint(valpos)
    return valpos


def get_rows(xmlfile):
    DOMTree = xml.dom.minidom.parse(xmlfile)
    collection = DOMTree.documentElement
    rows = collection.getElementsByTagName("ROW")
    return rows


def create_library_resources(xmlfile, bulk):
    """Creates mls:Library resources"""

    print("------------------------------------------")
    print("------------------------------------------")
    print("create_library_resources")
    print("------------------------------------------")

    valpos = get_valpos(xmlfile)
    rows = get_rows(xmlfile)

    for row in rows:
        datas = row.getElementsByTagName("DATA")
        i = 0
        record = {}
        for data in datas:
            if data.firstChild is not None:
                if valpos[i] == "PK_Bibl":
                    id = data.firstChild.nodeValue
                if valpos[i] == "Beschreibung":
                    record["hasLibrarydescription"] = data.firstChild.nodeValue
                if valpos[i] == "Bibliothekssigle_ohne_Land":
                    record["hasSigle"] = data.firstChild.nodeValue
                if valpos[i] == "Online_Katalog":
                    record["hasCatalogue"] = data.firstChild.nodeValue.strip("#")
                if valpos[i] == "Web_site":
                    record["hasLibraryweblink"] = data.firstChild.nodeValue.strip("#")
            i += 1

        if record.get("hasSigle") is None:
            record["hasSigle"] = "XXX"

        print("------------------------------------------")
        print("ID=" + str(id))
        pprint(record)
        bulk.add_resource(
            'Library',
            'LIB_' + str(id), record["hasSigle"], record)
        print("------------------------------------------")


def create_lemma_resources(xmlfile, bulk):
    """Creates mls:Lemma resources"""

    print("------------------------------------------")
    print("------------------------------------------")
    print("create_lemma_resources")
    print("------------------------------------------")

    valpos = get_valpos(xmlfile)
    rows = get_rows(xmlfile)

    for row in rows:
        cols = row.getElementsByTagName("COL")
        i = 0
        record = {}
        for col in cols:
            datas = col.getElementsByTagName("DATA")  # some columns can have multiple data tags
            data = datas.item(0)  # we are only interested in the first one
            if data is not None:
                if data.firstChild is not None:  # and only look inside if there is some data inside the data tag
                    pprint(data.firstChild.nodeValue)
                    if valpos[i] == "PK_Lemma":
                        id = data.firstChild.nodeValue
                    if valpos[i] == "Lemma":
                        record["hasLemmaText"] = data.firstChild.nodeValue
                    if valpos[i] == "Geschlecht":
                        record["hasSex"] = get_list_node_iri("sex", sex_lut[data.firstChild.nodeValue])
                    if valpos[i] == "GND":
                        record["hasGND"] = data.firstChild.nodeValue
                    if valpos[i] == "Artikeltyp":
                        record["hasLemmatype"] = get_list_node_iri("articletype", article_type_lut[data.firstChild.nodeValue])
            i += 1

        print("------------------------------------------")
        print("ID=" + str(id))
        pprint(record)
        bulk.add_resource(
            'Lemma',
            'LM_' + str(id), id, record)
        print("------------------------------------------")


def create_lemma_location_resources(xmlfile, bulk):
    """Creates mls:LemmaLocation resources"""

    print("------------------------------------------")
    print("------------------------------------------")
    print("create_lemma_location_resources")
    print("------------------------------------------")

    valpos = get_valpos(xmlfile)
    rows = get_rows(xmlfile)

    for row in rows:
        datas = row.getElementsByTagName("DATA")
        i = 0
        record = {}
        for data in datas:
            if data.firstChild is not None:
                if valpos[i] == "PK_Lemma_x_Ort":
                    id = data.firstChild.nodeValue
                if valpos[i] == "PKF_Lemma":
                    record["hasLLLinkToLemma"] = 'LM_' + data.firstChild.nodeValue
                if valpos[i] == "PKF_Wert":
                    record["hasLLLinkToLocation"] = 'LOC_' + data.firstChild.nodeValue
                if valpos[i] == "Bezug zum Ort":
                    record["hasLLRelation"] = data.firstChild.nodeValue
                if valpos[i] == "Komentar":
                    record["hasLLComment"] = data.firstChild.nodeValue
            i += 1

        # filter out links to dead-ends
        if record.get("hasLLLinkToLocation") == "LOC_7":
            pass
        elif record.get("hasLLLinkToLocation") == "LOC_5541":
            pass
        elif record.get("hasLLLinkToLocation") == "LOC_5549":
            pass
        else:
            print("------------------------------------------")
            print("ID=" + str(id))
            pprint(record)
            bulk.add_resource(
                'LemmaLocation',
                'LL_' + str(id), id, record)
            print("------------------------------------------")


def create_location_resources(xmlfile, bulk):
    """Creates mls:Location resources"""

    print("------------------------------------------")
    print("------------------------------------------")
    print("create_location_resources")
    print("------------------------------------------")

    valpos = get_valpos(xmlfile)
    rows = get_rows(xmlfile)

    for row in rows:
        cols = row.getElementsByTagName("COL")
        i = 0
        record = {}
        for col in cols:
            datas = col.getElementsByTagName("DATA")  # some columns can have multiple data tags
            data = datas.item(0)  # we are only interested in the first one
            if data is not None:
                if data.firstChild is not None:
                    if valpos[i] == "PK_Wert":
                        id = data.firstChild.nodeValue
                    if valpos[i] == "Land":
                        record["hasCountry"] = data.firstChild.nodeValue
                    if valpos[i] == "Ortsname":
                        record["hasPlacename"] = data.firstChild.nodeValue
                    if valpos[i] == "Kanton 1":
                        record["hasCanton"] = data.firstChild.nodeValue
                    if valpos[i] == "Komentar Ort":
                        record["hasLocationComment"] = data.firstChild.nodeValue
            i += 1

        print("------------------------------------------")
        print("ID=" + str(id))
        pprint(record)
        bulk.add_resource(
            'Location',
            'LOC_' + str(id), id, record)
        print("------------------------------------------")


def create_lemma_occupation_resources(xmlfile, bulk):
    """Creates mls:LemmaOccupation resources"""

    print("------------------------------------------")
    print("------------------------------------------")
    print("create_lemma_occupation_resources")
    print("------------------------------------------")

    valpos = get_valpos(xmlfile)
    rows = get_rows(xmlfile)

    for row in rows:
        datas = row.getElementsByTagName("DATA")
        i = 0
        record = {}
        for data in datas:
            if data.firstChild is not None:
                if valpos[i] == "PK_Lemma_x_Wert":
                    id = data.firstChild.nodeValue
                if valpos[i] == "PKF_Lemma":
                    record["hasLOLinkToLemma"] = 'LM_' + data.firstChild.nodeValue
                if valpos[i] == "PKF_Wert":
                    record["hasLOLinkToOccupation"] = 'OCC_' + data.firstChild.nodeValue
                if valpos[i] == "Komentar":
                    record["hasLOComment"] = data.firstChild.nodeValue
            i += 1

        # filter out links to dead-ends
        if record.get("hasLOLinkToOccupation") == "OCC_3":
            pass
        elif record.get("hasLOLinkToOccupation") == "OCC_5368":
            pass
        elif record.get("hasLOLinkToOccupation") == "OCC_5518":
            pass
        else:
            print("------------------------------------------")
            print("ID=" + str(id))
            pprint(record)
            bulk.add_resource(
                'LemmaOccupation',
                'LO_' + str(id), id, record)
            print("------------------------------------------")


def create_occupation_resources(xmlfile, bulk):
    """Creates mls:Occupation resources"""

    print("------------------------------------------")
    print("------------------------------------------")
    print("create_occupations")
    print("------------------------------------------")

    valpos = get_valpos(xmlfile)
    rows = get_rows(xmlfile)

    for row in rows:
        cols = row.getElementsByTagName("COL")
        i = 0
        record = {}
        for col in cols:
            datas = col.getElementsByTagName("DATA")  # some columns can have multiple data tags
            data = datas.item(0)  # we are only interested in the first one
            if data is not None:
                if data.firstChild is not None:  # and only look inside if there is some data inside the data tag
                    if valpos[i] == "PK_Wert":
                        id = data.firstChild.nodeValue
                    if valpos[i] == "Wert_Personentätigkeit":
                        record["hasOccupation"] = data.firstChild.nodeValue
                    if valpos[i] == "Land":
                        record["hasOccupationCountry"] = data.firstChild.nodeValue
                    if valpos[i] == "Ortsname":
                        record["hasOccupationPlacename"] = data.firstChild.nodeValue
                    if valpos[i] == "Kanton 1":
                        record["hasOccupationCanton"] = data.firstChild.nodeValue
            i += 1

        print("------------------------------------------")
        print("ID=" + str(id))
        pprint(record)
        bulk.add_resource(
            'Occupation',
            'OCC_' + str(id), id, record)
        print("------------------------------------------")


BULKIMPORT_API_ENDPOINT="http://localhost:3333/v1/resources/xmlimport/http%3A%2F%2Frdfh.ch%2Fprojects%2F0807"
headers = {"Content-Type": "application/xml"}
artikel_xml = './data/artikel.xml'
bibliotheken_xml = './data/bibliotheken.xml'
exemplar_xml = './data/exemplar.xml'
lemma_xml = './data/lemma.xml'
lemma1_x_lemma2_xml = './data/lemma1_x_lemma2.xml'
lemma_x_ort_xml = './data/lemma_x_ort.xml'
lemma_x_wert_xml = './data/lemma_x_wert.xml'
lexikon_xml = './data/lexikon.xml'
titelA_x_titelB_xml = './data/titelA_x_titelB.xml'
werte_orte_xml = './data/werte_orte.xml'
werte_personentaetigkeit_xml = './data/werte_personentaetigkeit.xml'

# create Library resources
# library_bulk_xml="mls-library-bulk.xml"
# library_bulk_object = BulkImport(schema)
# create_library_resources(bibliotheken_xml, library_bulk_object)
# library_bulk_object.write_xml(library_bulk_xml)

# create mls:Lemma resources
lemma_bulk_xml="mls-lemma-bulk.xml"
lemma_bulk_object = BulkImport(schema)
create_lemma_resources(lemma_xml, lemma_bulk_object)
lemma_bulk_object.write_xml(lemma_bulk_xml)
bulk_xml_string = open(lemma_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=bulk_xml_string, headers=headers, auth=('root@example.com', 'test'))
lemma_iris_json = r.json()
pprint(lemma_iris_json)

# {'createdResources': [{'clientResourceID': 'LM_1',
#                        'label': '1',
#                        'resourceIri': 'http://rdfh.ch/0807/rNxoIK-oR_i0-lO21Y9-CQ'},
#                       {'clientResourceID': 'LM_2']}

# create Location resources
# create_location_resources(werte_orte_xml, bulk_object)

# create LemmaLocation resources
# create_lemma_location_resources(lemma_x_ort_xml, bulk_object)



# create LemmaOccupation resources
# create_lemma_occupation_resources(lemma_x_wert_xml, bulk_object)

# create Occupation resources
#create_occupation_resources(werte_personentaetigkeit_xml, bulk_object)

# write the bulk import xml

