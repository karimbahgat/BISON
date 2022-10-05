
import requests

def iter_git_folders(path):
    owner = 'wmgeolab'
    repo = 'geoContrast'
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    resp = requests.get(url)
    for item in resp.json():
        yield item['path']
