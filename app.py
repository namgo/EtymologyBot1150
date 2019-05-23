import requests
import json
import re
import random
import logging
import facebook
from azure.cognitiveservices.search.imagesearch import ImageSearchAPI
from azure.cognitiveservices.search.imagesearch.models import SafeSearch
from msrest.authentication import CognitiveServicesCredentials

MAX_RETRIES = 4
SEP_WORDS = ['German','Latin','English','Greek','Germanic','French','Dutch']

with open("creds.json", "r") as f:
    creds = json.load(f)

# returns str
def _get_word(filename="OED_processed.txt"):
    with open("OED_processed.txt", "r") as f:
        dictionary = f.readlines()
    word = dictionary[random.randint(0, len(dictionary))].strip("\n")
    logging.info("got word {}".format(word))
    return word

def get_word():
    word = _get_word()
    while not word:
        logging.warn("couldn't find word, trying again")
        word = _get_word()
        if len(word) < 3 or word[len(word)] == '-':
            word = _get_word()
    return word
    

# returns json object
def etym_fetch(word_id, api_id, api_key, language="en-gb"):
    url = "https://od-api.oxforddictionaries.com:443/api/v2/entries/" + language + "/" + word_id.lower()
    r = requests.get(url, headers={"app_id": api_id, "app_key": api_key}) 
    json = r.json()
    return json

def get_image(word, api_key, endpoint):
    client = ImageSearchAPI(CognitiveServicesCredentials(api_key), base_url=endpoint,)
    data = client.images.search(
        query=word,
        safe_search=SafeSearch.strict
    )
    if data.value:
        first_image = data.value[0]
        logging.info("got image url {}".format(first_image.content_url))
        img = requests.get(first_image.content_url).content
        if not img:
            logging.warn("couldn't download image")
            raise ValueError("couldn't download image")
        return img
    else:
        logging.warn("couldn't find image")
        raise ValueError("couldn't find image")

def get_etymology_and_definition_text(etym):
    etym_text = ''
    definition_text = ''
    for result in etym['results']:
        for l_entry in result['lexicalEntries']:
            for entry in l_entry['entries']:
                try:
                    definition_text = ''
                    for sense in entry['senses']:
                        for definition in sense['definitions']:
                            definition_text += '{}\n'.format(definition)
                except KeyError:
                    pass
                try:
                    etym_text = ''
                    for etymology in entry['etymologies']:
                        etym_text += '{}\n'.format(etymology)
                except KeyError:
                    continue
            if etym_text:
                return {
                    'definition': definition_text,
                    'etymology': etym_text
                }
    raise ValueError("couldn't find etymology")

def separate(etym_text):
    for sep in SEP_WORDS:
        if sep in etym_text:
            etym_text = etym_text.replace(sep, ' {} '.format(sep))
    return etym_text

success = True
graph = facebook.GraphAPI(access_token=creds['facebook']['token'], version='3.1')
# try until success of MAX_RETRIES
for i in range(0,MAX_RETRIES):
    word = get_word()
    try:
        success = True
        try:
            img = get_image(get_word(), creds['azure']['key'], creds['azure']['endpoint'])
        except:
            with open('404.JPG', 'rb') as f:
                img = f.read()
        etym = etym_fetch(word, creds['oed']['id'], creds['oed']['key'])
        text_dict = get_etymology_and_definition_text(etym)
        text = '{}\nDefinition: {}\nEtymology: {}'.format(
            word,
            text_dict['definition'],
            separate(text_dict['etymology'])
        )
        graph.put_photo(image=img, message=text)
        break
    except Exception as e:
        logging.error(e)
        success = False
        continue

if not success:
    logging.fatal("couldn't successfully send")
