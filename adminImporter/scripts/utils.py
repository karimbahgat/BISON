
import requests

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
