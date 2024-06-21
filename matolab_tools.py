import re
import json
import requests

csvtocsvw_url='https://csvtocsvw.matolab.org'
maptomethod_url='https://maptomethod.matolab.org'
rdfconverter_url='https://rdfconverter.matolab.org'
meta_extractor_api = "https://metadata.omero.matolab.org/api/"


def post_request(url, headers, data, files=None):
    try:
        if files:
            # should crate a multipart form upload
            response = requests.post(
                url, data=data, headers=headers, files=files)
        else:
            # a application json post request
            response = requests.post(
                url, data=json.dumps(data), headers=headers)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        # placeholder for save file / clean-up
        raise SystemExit(e) from None
    return response


def annotate_csv_uri(csv_url: str, encoding: str = 'auto',):
    # curl -X 'POST' \ 'https://csvtocsvw.matolab.org/api/annotation' \ -H 'accept: application/json' \ -H 'Content-Type: application/json' \ -d '{ "data_url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example.csv", "separator": "auto", "header_separator": "auto", "encoding": "auto" }'
    url = csvtocsvw_url+"/api/annotate"
    data = {
        "data_url": csv_url,
        "encoding": encoding
    }
    headers = {'Content-type': 'application/json',
               'Accept': 'application/json'}
    r = post_request(url, headers, data)
    if r.status_code == 200:
        d = r.headers["content-disposition"]
        mime_type = r.headers["content-type"]
        filename = re.findall("filename=(.+)", d)[0]
        file=r.content
        print("csvw annotation file created, suggested name: {}".format(filename))
        with open(filename, "wb") as f:
            f.write(file)
            print('wrote csvw meta data to {}'.format(filename))
        return True



def annotate_csv_upload(filepath: str, encoding: str = 'auto',):
    # curl -X 'POST' \ 'https://csvtocsvw.matolab.org/api/annotate_upload?encoding=auto' \ -H 'accept: application/json' \ -H 'Content-Type: multipart/form-data' \ -F 'file=@detection_runs.csv;type=text/csv'
    url = csvtocsvw_url+"/api/annotate_upload?encoding=auto"
    headers = {"accept": "application/json"}
    head, tail = os.path.split(filepath)
    files = {"file": (tail, open(filepath, "rb"), "text/csv")}
    response = requests.post(url, headers=headers, files=files)
    if response.status_code == 200:
        return response.json()
    else:
        return response


def csvw_to_rdf(meta_url: str, format: str = 'turtle',):
    # curl -X 'POST' \ 'https://csvtocsvw.matolab.org/api/rdf' \ -H 'accept: application/json' \ -H 'Content-Type: application/json' \ -d '{ "metadata_url": "https://github.com/Mat-O-Lab/resources/raw/main/rdfconverter/tests/detection_runs-metadata.json", "format": "turtle" }'
    url = csvtocsvw_url+"/api/rdf"
    data = {
        "metadata_url": meta_url,
        "format": format
    }
    headers = {'Content-type': 'application/json',
               'Accept': 'application/json'}
    #r = requests.post(url, data=json.dumps(data), headers=headers)
    r = post_request(url, headers, data)
    if r.status_code == 200:
        d = r.headers['content-disposition']
        fname = re.findall("filename=(.+)", d)[0]
        with open(fname, 'wb') as f:
            f.write(r.content)
        print('writen serialized table to {}'.format(fname))
        return True
    else:
        return False


def create_mapping(meta_url: str, method_url: str, use_template_rowwise: bool, map_dict: dict, data_super_classes: list, predicate: str, method_super_classes: list):
    # curl -X 'POST' \ 'https://csvtocsvw.matolab.org/api/annotation' \ -H 'accept: application/json' \ -H 'Content-Type: application/json' \ -d '{ "data_url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example.csv", "separator": "auto", "header_separator": "auto", "encoding": "auto" }'
    url = maptomethod_url+"/api/mapping"
    data = {
        "data_url": meta_url,
        "method_url": method_url,
        "use_template_rowwise": use_template_rowwise,
        "data_super_classes": data_super_classes,
        "predicate": predicate,
        "method_super_classes": method_super_classes,
        "map": map_dict
    }
    headers = {'Content-type': 'application/json',
               'Accept': 'application/json'}
    r = post_request(url, headers, data)
    if r.status_code == 200:
        d = r.headers['content-disposition']
        fname = re.findall("filename=(.+)", d)[0]
        with open(fname, 'wb') as f:
            f.write(r.content)
        print('writen mapping file to {}'.format(fname))
        return True
    else:
        return False


def get_joined_rdf(map_url: str, data_url: str, duplicate_for_table=False):
    # curl -X 'POST' \ 'https://csvtocsvw.matolab.org/api/annotation' \ -H 'accept: application/json' \ -H 'Content-Type: application/json' \ -d '{ "data_url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example.csv", "separator": "auto", "header_separator": "auto", "encoding": "auto" }'
    url = rdfconverter_url+"/api/createrdf"
    data = {
        "mapping_url": map_url,
        "data_url": data_url
    }
    headers = {'Content-type': 'application/json',
               'Accept': 'application/json'}
    r = post_request(url, headers, data)
    if r.status_code == 200:
        r=r.json()
        filename=r['filename']
        print("applied {} mapping rules and skipped {}".format(r['num_mappings_applied'],r['num_mappings_skipped']))
        with open(filename, "wb") as f:
            f.write(r['graph'].encode())
            print('wrote joint graph to {}'.format(filename))
    else:
        return r
