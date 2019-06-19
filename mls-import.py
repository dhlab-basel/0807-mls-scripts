import argparse
from pprint import pprint
from knora import KnoraError, Knora, BulkImport, IrisLookup, ListsLookup
from xml.dom.minidom import parse
import xml.dom.minidom
import json
import datetime
import jdcal
import os
import sys
import inspect

article_type_lut = {
        'Person': 'person',
        'Sache': 'thing',
        'Ort': 'location',
        'Institution': 'institution',
        'Liste': 'List'
}

sex_lut = {
        'männlich': 'male',
        'weiblich': 'female',
        'weiblich & männliche Gruppe': 'male+female'
}


# converts the deceased key into a unique value
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
ll = ListsLookup(json.loads(lists_json_string))


def get_valpos(xmlfile, debug: bool = False):
    DOMTree = xml.dom.minidom.parse(xmlfile)
    collection = DOMTree.documentElement
    fields = collection.getElementsByTagName("FIELD")

    valpos = []
    for field in fields:
        name = field.getAttribute('NAME')
        valpos.append(name)

    if debug is True:
        pprint(valpos)

    return valpos


def get_rows(xmlfile):
    DOMTree = xml.dom.minidom.parse(xmlfile)
    collection = DOMTree.documentElement
    rows = collection.getElementsByTagName("ROW")
    return rows


def create_library_resources(xmlfile, bulk: BulkImport, debug: bool = False):
    """Creates mls:Library resources"""
    print("==> {0} started ...".format(inspect.currentframe().f_code.co_name ))

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

        if debug is True:
            print("------------------------------------------")
            print("ID=" + str(rec_id))
            pprint(record)
            print("------------------------------------------")
        bulk.add_resource(
            'Library',
            'LIB_' + str(rec_id), record["hasSigle"], record)

    print("==> ... {0} - {1} - finished.".format(inspect.currentframe().f_code.co_name, rows.length))


def create_lemma_resources(xmlfile, bulk: BulkImport, debug: bool = False):
    """Creates mls:Lemma resources"""
    print("==> {0} started ...".format(inspect.currentframe().f_code.co_name ))

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
                        rec_label = data.firstChild.nodeValue

                    if valpos[i] == "Geschlecht":
                        record["hasSex"] = ll.get_list_node_iri("sex", sex_lut[data.firstChild.nodeValue])

                    if valpos[i] == "GND":
                        record["hasGND"] = data.firstChild.nodeValue

                    if valpos[i] == "Anfangasdatum":
                        record["hasStartDate"] = data.firstChild.nodeValue

                    if valpos[i] == "Information_Anfangsdatum":
                        record["hasStartDateInfo"] = data.firstChild.nodeValue

                    if valpos[i] == "Artikeltyp":
                        record["hasLemmaType"] = ll.get_list_node_iri("articletype",
                                                                      article_type_lut[data.firstChild.nodeValue])

                    if valpos[i] == "Enddatum":
                        record["hasEndDate"] = data.firstChild.nodeValue

                    if valpos[i] == "Information_Enddatum":
                        record["hasEndDateInfo"] = data.firstChild.nodeValue

                    if valpos[i] == "Jahrhundertangabe":
                        record["hasCentury"] = data.firstChild.nodeValue

                    if valpos[i] == "Familienname":
                        record["hasFamilyName"] = data.firstChild.nodeValue

                    if valpos[i] == "Vorname":
                        record["hasGivenName"] = data.firstChild.nodeValue

                    if valpos[i] == "Pseudonym":
                        record["hasPseudonym"] = data.firstChild.nodeValue

                    if valpos[i] == "Relevantes Lemma":
                        record["hasRelevanceValue"] = ll.get_list_node_iri("relevance",
                                                                           convert_relevance_key(data.firstChild.nodeValue))

                    if valpos[i] == "Varianten":
                        record["hasVariants"] = data.firstChild.nodeValue

                    if valpos[i] == "Verstorben":
                        record["hasDeceasedValue"] = ll.get_list_node_iri("deceased",
                                                                          convert_deceased_key(data.firstChild.nodeValue))

                    if valpos[i] == "VIAF":
                        record["hasViaf"] = data.firstChild.nodeValue
            i += 1

        if record.get("hasLemmaText") is None:
            record["hasLemmaText"] = "XXX"

        if debug is True:
            print("------------------------------------------")
            print("ID=" + str(rec_id))
            pprint(record)
            print("------------------------------------------")

        bulk.add_resource(
            'Lemma',
            'LM_' + str(rec_id), record["hasLemmaText"], record)

    print("==> ... {0} - {1} - finished.".format(inspect.currentframe().f_code.co_name, rows.length))


def create_occupation_resources(xmlfile, bulk: BulkImport, debug: bool = False):
    """Creates mls:Occupation resources"""
    print("==> {0} started ...".format(inspect.currentframe().f_code.co_name ))

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

        if debug is True:
            print("------------------------------------------")
            print("ID=" + str(rec_id))
            pprint(record)
            print("------------------------------------------")

        bulk.add_resource(
            'Occupation',
            'OCC_' + str(rec_id), rec_id, record)

    print("==> ... {0} - {1} - finished.".format(inspect.currentframe().f_code.co_name, rows.length))


def create_location_resources(xmlfile, bulk: BulkImport, debug: bool = False):
    """Creates mls:Location resources"""
    print("==> {0} started ...".format(inspect.currentframe().f_code.co_name ))

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

        if debug is True:
            print("------------------------------------------")
            print("ID=" + str(rec_id))
            pprint(record)
            print("------------------------------------------")

        bulk.add_resource(
            'Location',
            'LOC_' + str(rec_id), rec_id, record)

    print("==> ... {0} - {1} - finished.".format(inspect.currentframe().f_code.co_name, rows.length))


def create_lemma_occupation_resources(xmlfile, bulk: BulkImport, lemma_iris_lookup: IrisLookup, occupation_iris_lookup: IrisLookup, debug:bool = False):
    """Creates mls:LemmaOccupation resources"""
    print("==> {0} started ...".format(inspect.currentframe().f_code.co_name ))

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
                    record["hasLOLinkToLemma"] = lemma_iris_lookup.get_resource_iri('LM_' + data.firstChild.nodeValue)
                if valpos[i] == "PKF_Wert":
                    record["hasLOLinkToOccupation"] = occupation_iris_lookup.get_resource_iri('OCC_' + data.firstChild.nodeValue)
                if valpos[i] == "Komentar":
                    record["hasLOComment"] = data.firstChild.nodeValue
            i += 1

        # filter out links to dead-ends
        if record.get("hasLOLinkToLemma") is None:
            pass
        elif record.get("hasLOLinkToOccupation") is None:
            pass
        else:
            if debug is True:
                print("------------------------------------------")
                print("ID=" + str(rec_id))
                pprint(record)
                print("------------------------------------------")
            bulk.add_resource(
                'LemmaOccupation',
                'LO_' + str(rec_id), rec_id, record)

    print("==> ... {0} - {1} - finished.".format(inspect.currentframe().f_code.co_name, rows.length))


def create_lemma_location_resources(xmlfile, bulk: BulkImport, lemma_iris_lookup: IrisLookup, location_iris_lookup: IrisLookup, debug: bool = False):
    """Creates mls:LemmaLocation resources"""
    print("==> {0} started ...".format(inspect.currentframe().f_code.co_name ))

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
                    record["hasLLLinkToLemma"] = lemma_iris_lookup.get_resource_iri('LM_' + data.firstChild.nodeValue)
                if valpos[i] == "PKF_Wert":
                    record["hasLLLinkToLocation"] = location_iris_lookup.get_resource_iri('LOC_' + data.firstChild.nodeValue)
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
            if debug is True:
                print("------------------------------------------")
                print("ID=" + str(rec_id))
                pprint(record)
                print("------------------------------------------")

            bulk.add_resource(
                'LemmaLocation',
                'LL_' + str(rec_id), rec_id, record)

    print("==> ... {0} - {1} - finished.".format(inspect.currentframe().f_code.co_name, rows.length))


def create_lexicon_resources(xmlfile, bulk: BulkImport, debug: bool = False):
    """Creates mls:Lexicon resources"""
    print("==> {0} started ...".format(inspect.currentframe().f_code.co_name ))

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

                    if valpos[i] == "kürzel":
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

        if debug is True:
            print("------------------------------------------")
            print("ID=" + str(rec_id))
            pprint(record)
            print("------------------------------------------")

        bulk.add_resource(
            'Lexicon',
            'LX_' + str(rec_id), rec_id, record)

    print("==> ... {0} - {1} - finished".format(inspect.currentframe().f_code.co_name, rows.length))


def create_article_resources(xmlfile, bulk: BulkImport, lemma_iris_lookup: IrisLookup, lexicon_iris_lookup: IrisLookup, debug: bool = False):
    """Creates mls:Article resources"""
    print("==> {0} started ...".format(inspect.currentframe().f_code.co_name ))

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
                        record["hasALinkToLemma"] = lemma_iris_lookup.get_resource_iri('LM_' + data.firstChild.nodeValue)
                    if valpos[i] == "PKF_Lexikon":
                        record["hasALinkToLexicon"] = lexicon_iris_lookup.get_resource_iri('LX_' + data.firstChild.nodeValue)
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

        if debug is True:
            print("------------------------------------------")
            print("ID=" + str(rec_id))
            pprint(record)
            print("------------------------------------------")

        bulk.add_resource(
            'Article',
            'A_' + str(rec_id), rec_id, record)

    print("==> ... {0} - {1} - finished.".format(inspect.currentframe().f_code.co_name, rows.length))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", type=str, default="http://0.0.0.0:3333", help="URL of the Knora server")
    #parser.add_argument("-u", "--user", type=str, default="mls0807import@example.com", help="Username for Knora")
    parser.add_argument("-u", "--user", type=str, default="root@example.com", help="Username for Knora")
    parser.add_argument("-p", "--password", type=str, default="test", help="The password for login")
    parser.add_argument("-P", "--projectcode", type=str, default="0807", help="Project short code")
    parser.add_argument("-O", "--ontoname", type=str, default="mls", help="Shortname of ontology")
    parser.add_argument("-x", "--xml", type=str, default="mls-bulk.xml", help="Name of bulk import XML-File")
    parser.add_argument("--start", default="1", help="Start with given line")
    parser.add_argument("--stop", default="all", help="End with given line ('all' reads all lines")

    args = parser.parse_args()

    con = Knora(args.server, args.user, args.password)
    schema = con.create_schema(args.projectcode, args.ontoname)

    exemplar_xml = './data/exemplar.xml'
    lemma1_x_lemma2_xml = './data/lemma1_x_lemma2.xml'
    titelA_x_titelB_xml = './data/titelA_x_titelB.xml'
    werte_personentaetigkeit_xml = './data/werte_personentaetigkeit.xml'

    if not os.path.exists("./out"):
        os.makedirs("./out")

    # create Library resources
    library_data_xml = './data/bibliotheken.xml'
    library_bulk_object = BulkImport(schema)
    create_library_resources(library_data_xml, library_bulk_object)
    print("==> Library upload start ...")
    r = library_bulk_object.upload(args.user, args.password, "localhost", "3333")
    library_iris_lookup = IrisLookup(r)
    print("==> Library upload finished.")

    # create mls:Lemma resources
    lemma_data_xml = './data/lemma.xml'
    lemma_bulk_object = BulkImport(schema)
    create_lemma_resources(lemma_data_xml, lemma_bulk_object, True)
    print("==> Lemma upload start ...")
    r = lemma_bulk_object.upload(args.user, args.password, "localhost", "3333")
    lemma_iris_lookup = IrisLookup(r)
    print("==> Lemma upload finished.")

    # create Occupation resources
    occupation_data_xml = './data/werte_personentaetigkeit.xml'
    occupation_bulk_object = BulkImport(schema)
    create_occupation_resources(occupation_data_xml, occupation_bulk_object)
    print("==> Occupation upload start ...")
    r = occupation_bulk_object.upload(args.user, args.password, "localhost", "3333")
    occupation_iris_lookup = IrisLookup(r)
    print("==> Occupation upload finished.")

    # create Location resources
    location_data_xml = './data/werte_orte.xml'
    location_bulk_object = BulkImport(schema)
    create_location_resources(location_data_xml, location_bulk_object)
    print("==> Location upload start ...")
    r = location_bulk_object.upload(args.user, args.password, "localhost", "3333")
    location_iris_lookup = IrisLookup(r)
    print("==> Location upload finished.")

    # create LemmaOccupation resources
    lemma_occupation_data_xml = './data/lemma_x_wert.xml'
    lemma_occupation_bulk_object = BulkImport(schema)
    create_lemma_occupation_resources(lemma_occupation_data_xml,
                                      lemma_occupation_bulk_object,
                                      lemma_iris_lookup,
                                      occupation_iris_lookup)
    print("==> LemmaOccupation upload start ...")
    r = lemma_occupation_bulk_object.upload(args.user, args.password, "localhost", "3333")
    lemma_occupation_iris_lookup = IrisLookup(r)
    print("==> LemmaOccupation upload finished.")

    # create LemmaLocation resources
    lemma_location_data_xml = './data/lemma_x_ort.xml'
    lemma_location_bulk_object = BulkImport(schema)
    create_lemma_location_resources(lemma_location_data_xml,
                                    lemma_location_bulk_object,
                                    lemma_iris_lookup,
                                    location_iris_lookup)
    print("==> LemmaLocation upload start ...")
    r = lemma_location_bulk_object.upload(args.user, args.password, "localhost", "3333")
    lemma_location_iris_lookup = IrisLookup(r)
    print("==> LemmaLocation upload finished.")

    # create Lexicon resources
    lexicon_data_xml = './data/lexikon.xml'
    lexicon_bulk_object = BulkImport(schema)
    create_lexicon_resources(lexicon_data_xml, lexicon_bulk_object)
    print("==> Lexicon upload start ...")
    r = lexicon_bulk_object.upload(args.user, args.password, "localhost", "3333")
    lexicon_iris_lookup = IrisLookup(r)
    print("==> Lexicon upload finished.")

    # create Article resources
    article_data_xml = './data/artikel.xml'
    article_bulk_object = BulkImport(schema)
    create_article_resources(article_data_xml,
                             article_bulk_object,
                             lemma_iris_lookup,
                             lexicon_iris_lookup)
    print("==> Article upload start ...")
    r = article_bulk_object.upload(args.user, args.password, "localhost", "3333")
    article_iris_lookup = IrisLookup(r)
    print("==> Article upload finished.")

    con = None
    sys.exit()


if __name__ == "__main__":
    main()
