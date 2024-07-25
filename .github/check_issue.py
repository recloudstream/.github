import httpx
import asyncio

import difflib

import os
import sys

import logging
import json

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

THRESHOLD = 0.95
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
            names.add(plugin['name'])
            names.add(plugin['internalName'])
            names.add(remove_suffix(plugin['name'], "Provider"))
            names.add(remove_suffix(plugin['internalName'], "Provider"))
        return [n for n in names if len(n) > 3]


async def fetch_names_repo(url):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            dat = r.json()
            plugin_lists = dat.get('pluginLists', [])
            results = []
            for plugin_url in plugin_lists:
                try:
                    names = await fetch_names_plugin_list(plugin_url)
                    results.extend(names)
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse JSON from plugin list URL: {plugin_url}\nRepository URL: {url}")
                    sys.exit(1)
            return results
    except json.JSONDecodeError:
        logging.error(f"Failed to parse JSON from repository URL: {url}")
        sys.exit(1)
    except httpx.RequestError as e:
        logging.error(f"Request failed for URL {url}: {e}")
        sys.exit(1)


async def fetch_names():
    async with httpx.AsyncClient() as client:
        r = await client.get(DB_URL)
        data = r.json()
        urls = [entry.get('url') if isinstance(entry, dict) else entry for entry in data]
        results = await asyncio.gather(*[fetch_names_repo(url) for url in urls])
        return [el for sublist in results for el in sublist]


def matches(large_string, query_string, threshold):
    words = large_string.split()
    for word in words:
        s = difflib.SequenceMatcher(None, word, query_string)
        match = ''.join(word[i:i+n] for i, j, n in s.get_matching_blocks() if n)
        if len(match) / float(len(query_string)) >= threshold:
            yield match


plugin_names = asyncio.run(fetch_names())

text = os.getenv("GH_TEXT", "").lower()
for name in plugin_names:
    if name.lower() == "example":
        continue
    try:
        _ = next(matches(text, name.lower(), THRESHOLD))
        print(name)
        sys.exit(0)
    except StopIteration:
        pass
print("none")
