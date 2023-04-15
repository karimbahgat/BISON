
import requests
from urllib.request import urlopen
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
