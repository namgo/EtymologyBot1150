import requests
import json
with open("creds.json", "r") as f:
    creds = json.load(f)
language = "en-gb"
word_id = "example"
url = "https://od-api.oxforddictionaries.com:443/api/v2/entries/" + language + "/" + word_id.lower()
r = requests.get(url, headers={"app_id": creds["id"], "app_key": creds["key"]}) 
print(r.json())

