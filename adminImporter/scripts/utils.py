
import requests
from urllib.request import urlopen, Request
import json

token = ''

def iter_git_folders(owner, repo, path):
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        resp = requests.get(url, headers=headers)
    else:
        resp = requests.get(url)
    data = resp.json()
    for item in data:
        yield item['path']

def get_metadata(url):
    return json.loads(urlopen(url).read())

def get_source_params_from_meta(meta):
    start = end = None
    yr = meta['year']
    if yr:
        start = '{}-01-01'.format(yr)
        end = '{}-12-31'.format(yr)
    source_params = {
        "type": "DataSource",
        "name": meta['source'],
        "valid_from": start,
        "valid_to": end,
        "url": meta.get('source_url', None),
        #"license": meta['license'],
        #"updated": meta['source_updated'],
    }
    return source_params

def post_datasource(host, meta):
    '''Creates a data source by sending a post request via the add datasource api.
    Takes a dict of kwargs needed to create a source, converts this to form data,
    submits, and returns the created source id as returned by the site.
    '''
    # post data params is about the same as the model kwargs
    post = meta
    url = f'{host}/api/datasets/add/'
    resp = requests.post(url, json=post)
    if not resp.ok:
        raise Exception(resp.reason)
    src_id = resp.json()['pk']
    src_id = int(src_id)
    return src_id

def post_datasource_importers(host, importers):
    '''Creates data importers by sending a post request via api endpoint.
    Takes a list of kwargs needed to create one or more importers, converts this to json data,
    and submits.
    '''
    src = importers[0]['source'] # all should have save source
    url = f'{host}/api/datasource/importers/add/{src}/'
    resp = requests.post(url, json=importers)
    if not resp.ok:
        raise Exception(resp.reason)

def inspect_zipfile_contents(url):
    # adapted from https://betterprogramming.pub/how-to-know-zip-content-without-downloading-it-87a5b30be20a
    import io
    import struct
    import zipfile
    import requests

    EOCD_RECORD_SIZE = 22
    ZIP64_EOCD_RECORD_SIZE = 56
    ZIP64_EOCD_LOCATOR_SIZE = 20

    MAX_STANDARD_ZIP_SIZE = 4_294_967_295

    headers = {"User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}

    def get_zip_file(url):
        file_size = get_file_size(url)
        eocd_record = fetch(url, file_size - EOCD_RECORD_SIZE, EOCD_RECORD_SIZE)
        if file_size <= MAX_STANDARD_ZIP_SIZE:
            cd_start, cd_size = get_central_directory_metadata_from_eocd(eocd_record)
            central_directory = fetch(url, cd_start, cd_size)
            return zipfile.ZipFile(io.BytesIO(central_directory + eocd_record))
        else:
            zip64_eocd_record = fetch(url,
                                    file_size - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE + ZIP64_EOCD_RECORD_SIZE),
                                    ZIP64_EOCD_RECORD_SIZE)
            zip64_eocd_locator = fetch(url,
                                    file_size - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE),
                                    ZIP64_EOCD_LOCATOR_SIZE)
            cd_start, cd_size = get_central_directory_metadata_from_eocd64(zip64_eocd_record)
            central_directory = fetch(url, cd_start, cd_size)
            return zipfile.ZipFile(io.BytesIO(central_directory + zip64_eocd_record + zip64_eocd_locator + eocd_record))

    def get_file_size(url):
        req = Request(url, headers=headers)
        resp = urlopen(req)
        return int(resp.headers['Content-Length'])

    def fetch(url, start, length):
        end = start + length - 1
        _headers = headers.copy()
        _headers['range'] = "bytes=%d-%d" % (start, end)
        #print('requesting', _headers)
        req = Request(url, headers=_headers)
        response = urlopen(req)
        #print('receiving', response.headers)
        return response.read()

    def get_central_directory_metadata_from_eocd(eocd):
        cd_size = parse_little_endian_to_int(eocd[12:16])
        cd_start = parse_little_endian_to_int(eocd[16:20])
        return cd_start, cd_size

    def get_central_directory_metadata_from_eocd64(eocd64):
        cd_size = parse_little_endian_to_int(eocd64[40:48])
        cd_start = parse_little_endian_to_int(eocd64[48:56])
        return cd_start, cd_size

    def parse_little_endian_to_int(little_endian_bytes):
        format_character = "i" if len(little_endian_bytes) == 4 else "q"
        return struct.unpack("<" + format_character, little_endian_bytes)[0]

    def iter_zip_content(zip_file):
        for zi in zip_file.filelist:
            yield zi.filename

    # process zipfile
    zip_file = get_zip_file(url)
    return iter_zip_content(zip_file)
