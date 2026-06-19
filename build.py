#!/usr/bin/env python3
"""Merge Persiana + News + Israel channels into one M3U with EPG."""
import json, re, os, urllib.request, zipfile, io

PERSIANA_M3U = "https://raw.githubusercontent.com/Samhouston010/persiana-tv-epg/main/final.m3u"
IDANPLUS_ZIP = "https://raw.githubusercontent.com/fishenzon/repo/master/zips/plugin.video.idanplus/plugin.video.idanplus-3.9.9.zip"
KESHET_BASE = "https://mako-streaming.akamaized.net"
SAMTV_KESHET_PROXY = "http://localhost:8080/api/keshet"

EPG_URLS = ",".join([
    "https://raw.githubusercontent.com/Samhouston010/persiana-tv-epg/main/all.xml.gz",
    "https://raw.githubusercontent.com/Samhouston010/sepehr-irib-epg/main/sepehr.xml.gz",
])

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read()

def get_persiana():
    data = fetch(PERSIANA_M3U).decode("utf-8")
    lines = data.strip().split("\n")
    if lines and lines[0].startswith("#EXTM3U"):
        lines = lines[1:]
    return "\n".join(lines)

def get_israel():
    data = fetch(IDANPLUS_ZIP)
    zf = zipfile.ZipFile(io.BytesIO(data))
    channels = json.loads(zf.read("plugin.video.idanplus/resources/channels.json"))

    lines = []
    for key, ch in channels.items():
        name = ch.get("name", key)
        link_info = ch.get("linkDetails", {})
        link = link_info.get("link", "")
        if not link:
            continue
        if link.startswith("/direct/") or link.startswith("/stream/"):
            link = SAMTV_KESHET_PROXY + link
        if not link.startswith("http"):
            continue

        img = ch.get("image", "")
        tvg_id = ch.get("tvgID", "")
        group = "Israel Radio" if key.startswith("rd_") else "Israel TV"

        lines.append(f'#EXTINF:-1 tvg-id="il_{tvg_id}" tvg-logo="{img}" group-title="{group}",{name}')
        lines.append(link)

    return "\n".join(lines)

def main():
    print("Fetching Persiana channels...")
    persiana = get_persiana()
    p_count = persiana.count("#EXTINF")
    print(f"  {p_count} channels")

    print("Fetching Israel channels from idanplus...")
    israel = get_israel()
    i_count = israel.count("#EXTINF")
    print(f"  {i_count} channels")

    header = f'#EXTM3U x-tvg-url="{EPG_URLS}"\n\n'

    m3u = header
    m3u += "## --- Persiana + Iran ---\n"
    m3u += persiana + "\n\n"
    m3u += "## --- Israel ---\n"
    m3u += israel + "\n"

    out = os.path.join(os.path.dirname(__file__), "final.m3u")
    with open(out, "w", encoding="utf-8") as f:
        f.write(m3u)

    total = p_count + i_count
    print(f"Done: {total} channels -> {out}")

if __name__ == "__main__":
    main()
