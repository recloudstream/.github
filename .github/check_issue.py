import httpx
import asyncio

import difflib

import os

THRESHOLD = 0.73
DB_URL = "https://raw.githubusercontent.com/recloudstream/cs-repos/master/repos-db.json"

def remove_suffix(text, suffix):
    if text.endswith(suffix):
        return text[:-len(suffix)]
    return text

async def fetch_names_plugin_list(url):
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        dat = r.json()
        names = set()
        for plugin in dat:
            names.add(remove_suffix(plugin['name'], "Provider"))
            names.add(remove_suffix(plugin['internalName'], "Provider"))
        return names
    
async def fetch_names_repo(url):
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        dat = r.json()
        res = await asyncio.gather(*[fetch_names_plugin_list(x) for x in dat['pluginLists']])
        return [el for sub in res for el in sub]

async def fetch_names():
    
    async with httpx.AsyncClient() as client:
        r = await client.get(DB_URL)
        dat = r.json()
        res = await asyncio.gather(*[fetch_names_repo(x) for x in dat])
        return [el for sub in res for el in sub]
    
def matches(large_string, query_string, threshold):
    words = large_string.split()
    for word in words:
        s = difflib.SequenceMatcher(None, word, query_string)
        match = ''.join(word[i:i+n] for i, j, n in s.get_matching_blocks() if n)
        if len(match) / float(len(query_string)) >= threshold:
            yield match

    
plugin_names = asyncio.run(fetch_names())

text = os.getenv("GH_TEXT").lower()
print("Body: ", text)

for name in plugin_names:
    try:
        _ = next(matches(text, name.lower(), THRESHOLD))
        print(name)
        exit(0)
    except StopIteration:
        pass
print("none")
