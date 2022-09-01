import requests
base_url = 'http://127.0.0.1:{}/{}'

r = requests.post(base_url.format(5000, 'init'))
r = requests.post(base_url.format(5000, 'run'), json={'duration': 0.02})
print(r.json())