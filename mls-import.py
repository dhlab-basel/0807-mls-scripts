import argparse
from pprint import pprint
from knora import KnoraError, knora, BulkImport
from xml.dom.minidom import parse
import xml.dom.minidom
import json
import requests
import datetime
import jdcal
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--server", type=str, default="http://0.0.0.0:3333", help="URL of the Knora server")
# parser.add_argument("-u", "--user", type=str, default="mls0807import@example.com", help="Username for Knora")
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
# sys.exit()

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


def convert_deceased_key(key):
    deceased_lut = {
        'Ja': 'dec_ja',
        'Nein': 'dec_nein',
        'IMW': 'dec_imw',
        'Umfeld': 'dec_umfeld',
        'Irrelevant': 'dec_irrelevant',
        'Verweis': 'dec_verweis',
        'Sache / Ort': 'dec_sache_ort',
    }

    try:
        res = deceased_lut[key]
    except KeyError:
        res = None

    return res


def convert_relevance_key(key):
    relevance_lut = {
        'Ja': 'rel_ja',
        '1': 'rel_1',
        '2': 'rel_2',
        '3': 'rel_3',
        '4': 'rel_4',
        '5': 'rel_5',
        'Nein': 'rel_nein',
        'Ausnahmefall': 'rel_ausnahmefall',
        'Sache / Ort': 'rel_sache_ort',
        'Irrelevant': 'rel_irrelevant'
    }

    try:
        res = relevance_lut[key]
    except KeyError:
        res = None

    return res



def convert_to_julian_day_count(datestring):

    # data cleaning
    if "." not in datestring:
        fmt = "%Y"
    else:
        fmt = '%d.%m.%Y'

    dt = datetime.datetime.strptime(datestring, fmt)
    jdc = sum(jdcal.gcal2jd(dt.year, dt.month, dt.day))
    print("convert_to_julian_day_count - datestring: " + datestring + ", JDC: " + str(jdc))
    return jdc


# load the lists.json file
lists_json_string = open("lists.json").read()
lists = json.loads(lists_json_string)


def get_list_iri(listname):
    return lists[listname]["id"]


def get_list_node_iri(listname, nodename):
    if nodename is not None:
        nodes = lists[listname]["nodes"]
        res = ""
        for node in nodes:
            try:
                res = node[nodename]["id"]
            except KeyError:
                pass

        if res == "":
            print("get_list_node_iri - nodename: " + nodename + ", iri: None")
            return None
        else:
            print("get_list_node_iri - nodename: " + nodename + ", iri: " + str(res))
            return res
    else:
        print("get_list_node_iri - nodename: None, iri: None")
        return None


def get_resource_iri(local_id, local_id_to_iri_json):
    # given the result of the builk import as json, allow retrieving the resource
    # IRI based on the local ID.
    # {'createdResources': [{'clientResourceID': 'LM_1',
    #                        'label': '1',
    #                        'resourceIri': 'http://rdfh.ch/0807/rNxoIK-oR_i0-lO21Y9-CQ'},
    #                       {'clientResourceID': 'LM_2']}
    try:
        resources = local_id_to_iri_json["createdResources"]
        iri = ""
        for resource in resources:
            try:
                res_id = resource["clientResourceID"]
                if res_id == local_id:
                    iri = resource["resourceIri"]
                else:
                    pass
            except KeyError:
                pass

        if iri == "":
            print("get_resource_iri - local_id: " + local_id + ", iri: " + str(None))
            return None
        else:
            print("get_resource_iri - local_id: " + local_id + ", iri: " + iri)
            return iri
    except KeyError:
        print("get_resource_iri - 'createdResources' not found")
        pprint(local_id_to_iri_json)



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
        rec_id = 0
        record = {}
        for data in datas:
            if data.firstChild is not None:
                if valpos[i] == "PK_Bibl":
                    rec_id = data.firstChild.nodeValue
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
        print("ID=" + str(rec_id))
        pprint(record)
        bulk.add_resource(
            'Library',
            'LIB_' + str(rec_id), record["hasSigle"], record)
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
        rec_id = 0
        i = 0
        record = {}
        for col in cols:
            datas = col.getElementsByTagName("DATA")  # some columns can have multiple data tags
            data = datas.item(0)  # we are only interested in the first one
            if data is not None:
                if data.firstChild is not None:  # and only look inside if there is some data inside the data tag
                    if valpos[i] == "PK_Lemma":
                        rec_id = data.firstChild.nodeValue

                    if valpos[i] == "Lemma":
                        record["hasLemmaText"] = data.firstChild.nodeValue

                    if valpos[i] == "Geschlecht":
                        record["hasSex"] = get_list_node_iri("sex", sex_lut[data.firstChild.nodeValue])

                    if valpos[i] == "GND":
                        record["hasGND"] = data.firstChild.nodeValue

                    if valpos[i] == "Anfangsdatum":
                        record["hasStartDate"] = data.firstChild.nodeValue

                    if valpos[i] == "Information_Anfangsdatum":
                        record["hasStartDateInfo"] = data.firstChild.nodeValue

                    if valpos[i] == "Artikeltyp":
                        record["hasLemmaType"] = get_list_node_iri("articletype", article_type_lut[data.firstChild.nodeValue])

                    if valpos[i] == "Enddatum":
                        record["hasEndDate"] = data.firstChild.nodeValue

                    if valpos[i] == "Information_Enddatum":
                        record["hasEndDateInfo"] = data.firstChild.nodeValue

                    if valpos[i] == "Familienname":
                        record["hasFamilyName"] = data.firstChild.nodeValue

                    if valpos[i] == "Vorname":
                        record["hasGivenName"] = data.firstChild.nodeValue

                    if valpos[i] == "Pseudonym":
                        record["hasPseudonym"] = data.firstChild.nodeValue

                    if valpos[i] == "Relevantes Lemma":
                        record["hasRelevanceValue"] = get_list_node_iri("relevance", convert_relevance_key(data.firstChild.nodeValue))

                    if valpos[i] == "Varianten":
                        record["hasVariants"] = data.firstChild.nodeValue

                    if valpos[i] == "Verstorben":
                        record["hasDeceasedValue"] = get_list_node_iri("deceased", convert_deceased_key(data.firstChild.nodeValue))

                    if valpos[i] == "VIAF":
                        record["hasViaf"] = data.firstChild.nodeValue
            i += 1

        print("------------------------------------------")
        print("ID=" + str(rec_id))
        pprint(record)
        bulk.add_resource(
            'Lemma',
            'LM_' + str(rec_id), rec_id, record)
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
        rec_id = 0
        record = {}
        for col in cols:
            datas = col.getElementsByTagName("DATA")  # some columns can have multiple data tags
            data = datas.item(0)  # we are only interested in the first one
            if data is not None:
                if data.firstChild is not None:  # and only look inside if there is some data inside the data tag
                    if valpos[i] == "PK_Wert":
                        rec_id = data.firstChild.nodeValue
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
        print("ID=" + str(rec_id))
        pprint(record)
        bulk.add_resource(
            'Occupation',
            'OCC_' + str(rec_id), rec_id, record)
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
        rec_id = 0
        record = {}
        for col in cols:
            datas = col.getElementsByTagName("DATA")  # some columns can have multiple data tags
            data = datas.item(0)  # we are only interested in the first one
            if data is not None:
                if data.firstChild is not None:
                    if valpos[i] == "PK_Wert":
                        rec_id = data.firstChild.nodeValue
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
        print("ID=" + str(rec_id))
        pprint(record)
        bulk.add_resource(
            'Location',
            'LOC_' + str(rec_id), rec_id, record)
        print("------------------------------------------")


def create_lemma_occupation_resources(xmlfile, bulk, lemma_resource_iris, occupation_resource_iris):
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
        rec_id = 0
        record = {}
        for data in datas:
            if data.firstChild is not None:
                if valpos[i] == "PK_Lemma_x_Wert":
                    rec_id = data.firstChild.nodeValue
                if valpos[i] == "PKF_Lemma":
                    record["hasLOLinkToLemma"] = get_resource_iri('LM_' + data.firstChild.nodeValue, lemma_resource_iris)
                if valpos[i] == "PKF_Wert":
                    record["hasLOLinkToOccupation"] = get_resource_iri('OCC_' + data.firstChild.nodeValue, occupation_resource_iris)
                if valpos[i] == "Komentar":
                    record["hasLOComment"] = data.firstChild.nodeValue
            i += 1

        # filter out links to dead-ends
        if record.get("hasLOLinkToLemma") is None:
            pass
        elif record.get("hasLOLinkToOccupation") is None:
            pass
        else:
            print("------------------------------------------")
            print("ID=" + str(rec_id))
            pprint(record)
            bulk.add_resource(
                'LemmaOccupation',
                'LO_' + str(rec_id), rec_id, record)
            print("------------------------------------------")


def create_lemma_location_resources(xmlfile, bulk, lemma_resource_iris, location_resource_iris):
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
        rec_id = 0
        record = {}
        for data in datas:
            if data.firstChild is not None:
                if valpos[i] == "PK_Lemma_x_Ort":
                    rec_id = data.firstChild.nodeValue
                if valpos[i] == "PKF_Lemma":
                    record["hasLLLinkToLemma"] = get_resource_iri('LM_' + data.firstChild.nodeValue, lemma_resource_iris)
                if valpos[i] == "PKF_Wert":
                    record["hasLLLinkToLocation"] = get_resource_iri('LOC_' + data.firstChild.nodeValue, location_resource_iris)
                if valpos[i] == "Bezug zum Ort":
                    record["hasLLRelation"] = data.firstChild.nodeValue
                if valpos[i] == "Komentar":
                    record["hasLLComment"] = data.firstChild.nodeValue
            i += 1

        # filter out links to dead-ends
        if record.get("hasLLLinkToLemma") is None:
            pass
        elif record.get("hasLLLinkToLocation") is None:
            pass
        else:
            print("------------------------------------------")
            print("ID=" + str(rec_id))
            pprint(record)
            bulk.add_resource(
                'LemmaLocation',
                'LL_' + str(rec_id), rec_id, record)
            print("------------------------------------------")


def create_lexicon_resources(xmlfile, bulk):
    """Creates mls:Lexicon resources"""

    print("------------------------------------------")
    print("------------------------------------------")
    print("create_Lexicon_resources")
    print("------------------------------------------")

    valpos = get_valpos(xmlfile)
    rows = get_rows(xmlfile)

    for row in rows:
        cols = row.getElementsByTagName("COL")
        i = 0
        rec_id = 0
        record = {}
        for col in cols:
            datas = col.getElementsByTagName("DATA")  # some columns can have multiple data tags
            data = datas.item(0)  # we are only interested in the first one
            if data is not None:
                if data.firstChild is not None:
                    if valpos[i] == "PK_Lexikon":
                        rec_id = data.firstChild.nodeValue

                    if valpos[i] == "Zitierform":
                        record["hasCitationForm"] = data.firstChild.nodeValue

                    if valpos[i] == "kürzele":
                        record["hasShortname"] = data.firstChild.nodeValue

                    if valpos[i] == "Zitierform":
                        record["hasCitationForm"] = data.firstChild.nodeValue

                    if valpos[i] == "Komentar":
                        record["hasLexiconComment"] = data.firstChild.nodeValue

                    if valpos[i] == "Scan bearbeitet von":
                        record["hasScanVendor"] = data.firstChild.nodeValue

                    if valpos[i] == "Scan fertig":
                        record["hasScanFinished"] = data.firstChild.nodeValue

                    if valpos[i] == "OCR bearbeitet von":
                        record["hasOCRVendor"] = data.firstChild.nodeValue

                    if valpos[i] == "OCR fertig":
                        record["hasOCRFinished"] = data.firstChild.nodeValue

                    if valpos[i] == "Einträge bearbeitet von":
                        record["hasEditVendor"] = data.firstChild.nodeValue

                    if valpos[i] == "Einträge fertig":
                        record["hasEditFinished"] = data.firstChild.nodeValue

                    if valpos[i] == "Jahr":
                        record["hasYear"] = data.firstChild.nodeValue

            i += 1

        print("------------------------------------------")
        print("ID=" + str(rec_id))
        pprint(record)
        bulk.add_resource(
            'Lexicon',
            'LX_' + str(rec_id), rec_id, record)
        print("------------------------------------------")


def create_article_resources(xmlfile, bulk, lemma_resource_iris, lexicon_resource_iris):
    """Creates mls:Article resources"""

    print("------------------------------------------")
    print("------------------------------------------")
    print("create_article_resources")
    print("------------------------------------------")

    valpos = get_valpos(xmlfile)
    rows = get_rows(xmlfile)

    for row in rows:
        cols = row.getElementsByTagName("COL")
        i = 0
        rec_id = 0
        record = {}
        for col in cols:
            datas = col.getElementsByTagName("DATA")  # some columns can have multiple data tags
            data = datas.item(0)  # we are only interested in the first one
            if data is not None:
                if data.firstChild is not None:
                    if valpos[i] == "PK_Artikel":
                        rec_id = data.firstChild.nodeValue
                    if valpos[i] == "PKF_Lemma":
                        record["hasALinkToLemma"] = get_resource_iri('LM_' + data.firstChild.nodeValue,
                                                                                        lemma_resource_iris)
                    if valpos[i] == "PKF_Lexikon":
                        record["hasALinkToLexicon"] = get_resource_iri('LX_' + data.firstChild.nodeValue,
                                                                                        lexicon_resource_iris)
                    if valpos[i] == "Seite":
                        record["hasPages"] = data.firstChild.nodeValue

                    if valpos[i] == "Artikel":
                        record["hasArticleText"] = data.firstChild.nodeValue

                    if valpos[i] == "Zeilen":
                        record["hasNumLines"] = data.firstChild.nodeValue

                    if valpos[i] == "Kommentar":
                        record["hasArticleComment"] = data.firstChild.nodeValue

                    if valpos[i] == "Zustand":
                        record["hasState"] = data.firstChild.nodeValue

                    if valpos[i] == "Interne Lexicographische Information":
                        record["hasInternalLex"] = data.firstChild.nodeValue

                    if valpos[i] == "Link":
                        record["hasWebLink"] = data.firstChild.nodeValue

                    if valpos[i] == "Kurzinformation":
                        record["hasShortInfo"] = data.firstChild.nodeValue

                    if valpos[i] == "Theaterlexikon Code":
                        record["hasTheaterLexCode"] = data.firstChild.nodeValue

                    if valpos[i] == "Dizionario Ticinese Code":
                        record["hasTicinoLexCode"] = data.firstChild.nodeValue

                    if valpos[i] == "Fonoteca Code":
                        record["hasFonotecacode"] = data.firstChild.nodeValue

                    if valpos[i] == "HLS Code":
                        record["hasHlsCcode"] = data.firstChild.nodeValue

                    if valpos[i] == "OEML Code":
                        record["hasOemlCode"] = data.firstChild.nodeValue
            i += 1

        print("------------------------------------------")
        print("ID=" + str(rec_id))
        pprint(record)
        bulk.add_resource(
            'Article',
            'A_' + str(rec_id), rec_id, record)
        print("------------------------------------------")


BULKIMPORT_API_ENDPOINT="http://localhost:3333/v1/resources/xmlimport/http%3A%2F%2Frdfh.ch%2Fprojects%2F0807"
headers = {"Content-Type": "application/xml"}
exemplar_xml = './data/exemplar.xml'
lemma1_x_lemma2_xml = './data/lemma1_x_lemma2.xml'
titelA_x_titelB_xml = './data/titelA_x_titelB.xml'
werte_personentaetigkeit_xml = './data/werte_personentaetigkeit.xml'

if not os.path.exists("./out"):
    os.makedirs("./out")

# create Library resources
library_data_xml = './data/bibliotheken.xml'
library_bulk_xml = "./out/mls-library-bulk.xml"
library_bulk_object = BulkImport(schema)
create_library_resources(library_data_xml, library_bulk_object)
library_bulk_object.write_xml(library_bulk_xml)
library_bulk_xml_string = open(library_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=library_bulk_xml_string, headers=headers, auth=(args.user,
                                                                                                args.password))
library_iris_json = r.json()

# create mls:Lemma resources
lemma_data_xml = './data/lemma.xml'
lemma_bulk_xml = "./out/mls-lemma-bulk.xml"
lemma_bulk_object = BulkImport(schema)
create_lemma_resources(lemma_data_xml, lemma_bulk_object)
lemma_bulk_object.write_xml(lemma_bulk_xml)
lemma_bulk_xml_string = open(lemma_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=lemma_bulk_xml_string, headers=headers, auth=(args.user,
                                                                                              args.password))
lemma_iris_json = r.json()

# create Occupation resources
occupation_data_xml = './data/werte_personentaetigkeit.xml'
occupation_bulk_xml = "./out/mls-occupation-bulk.xml"
occupation_bulk_object = BulkImport(schema)
create_occupation_resources(occupation_data_xml, occupation_bulk_object)
occupation_bulk_object.write_xml(occupation_bulk_xml)
occupation_bulk_xml_string = open(occupation_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=occupation_bulk_xml_string, headers=headers, auth=(args.user,
                                                                                                   args.password))
occupation_iris_json = r.json()

# create Location resources
location_data_xml = './data/werte_orte.xml'
location_bulk_xml = "./out/mls-location-bulk.xml"
location_bulk_object = BulkImport(schema)
create_location_resources(location_data_xml, location_bulk_object)
location_bulk_object.write_xml(location_bulk_xml)
location_bulk_xml_string = open(location_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=location_bulk_xml_string, headers=headers, auth=(args.user,
                                                                                                 args.password))
location_iris_json = r.json()

# create LemmaOccupation resources
lemma_occupation_data_xml = './data/lemma_x_wert.xml'
lemma_occupation_bulk_xml = "./out/mls-lemma-occupation-bulk.xml"
lemma_occupation_bulk_object = BulkImport(schema)
create_lemma_occupation_resources(lemma_occupation_data_xml,
                                  lemma_occupation_bulk_object,
                                  lemma_iris_json,
                                  occupation_iris_json)
lemma_occupation_bulk_object.write_xml(lemma_occupation_bulk_xml)
lemma_occupation_bulk_xml_string = open(lemma_occupation_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=lemma_occupation_bulk_xml_string, headers=headers, auth=(args.user,
                                                                                                         args.password))
lemma_occupation_iris_json = r.json()


# create LemmaLocation resources
lemma_location_data_xml = './data/lemma_x_ort.xml'
lemma_location_bulk_xml = "./out/mls-lemma-location-bulk.xml"
lemma_location_bulk_object = BulkImport(schema)
create_lemma_location_resources(lemma_location_data_xml,
                                lemma_location_bulk_object,
                                lemma_iris_json,
                                location_iris_json)
lemma_location_bulk_object.write_xml(lemma_location_bulk_xml)
lemma_location_bulk_xml_string = open(lemma_location_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=lemma_location_bulk_xml_string, headers=headers, auth=(args.user,
                                                                                                       args.password))
lemma_location_iris_json = r.json()

# create Lexicon resources
lexicon_data_xml = './data/lexikon.xml'
lexicon_bulk_xml = "./out/mls-lexicon-bulk.xml"
lexicon_bulk_object = BulkImport(schema)
create_lexicon_resources(lexicon_data_xml, lexicon_bulk_object)
lexicon_bulk_object.write_xml(lexicon_bulk_xml)
lexicon_bulk_xml_string = open(lexicon_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=lexicon_bulk_xml_string, headers=headers, auth=(args.user,
                                                                                                args.password))
lexicon_iris_json = r.json()

# create Article resources
article_data_xml = './data/artikel.xml'
article_bulk_xml = "./out/mls-article-bulk.xml"
article_bulk_object = BulkImport(schema)
create_article_resources(article_data_xml, article_bulk_object,
                         lemma_iris_json,
                         lexicon_iris_json)
article_bulk_object.write_xml(article_bulk_xml)
article_bulk_xml_string = open(article_bulk_xml).read().encode("utf-8")
r = requests.post(BULKIMPORT_API_ENDPOINT, data=article_bulk_xml_string, headers=headers, auth=(args.user,
                                                                                                args.password))
article_iris_json = r.json()