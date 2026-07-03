#!/usr/bin/env python3
"""Merge Persiana + News + Israel channels into one M3U with EPG."""
import json, re, os, shutil, subprocess, tempfile, urllib.request, zipfile, io

PERSIANA_M3U = "https://raw.githubusercontent.com/Samhouston010/persiana-tv-epg/main/final.m3u"
IDANPLUS_ZIP = "https://raw.githubusercontent.com/fishenzon/repo/master/zips/plugin.video.idanplus/plugin.video.idanplus-3.9.9.zip"
KESHET_BASE = "https://mako-streaming.akamaized.net"
SAMTV_KESHET_PROXY = "http://localhost:8080/api/keshet"

EPG_URLS = ",".join([
    "https://raw.githubusercontent.com/Samhouston010/persiana-tv-epg/main/all.xml.gz",
    "https://raw.githubusercontent.com/Samhouston010/sepehr-irib-epg/main/sepehr.xml.gz",
])

MBC_CHANNELS = [
    {"name": "MBC 1", "id": "MBC1.ae", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-1/15cf99af5de54063fdabfefe66adc075/index.m3u8"},
    {"name": "MBC 4", "id": "MBC4.ae", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-4/24f134f1cd63db9346439e96b86ca6ed/index.m3u8"},
    {"name": "MBC 5", "id": "MBC5.ae", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-5/ee6b000cee0629411b666ab26cb13e9b/index.m3u8"},
    {"name": "MBC Drama", "id": "MBCDrama.ae", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-drama/2c28a458e2f3253e678b07ac7d13fe71/index.m3u8"},
    {"name": "MBC+ Drama", "id": "MBCPlusDrama.sa", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-plus-drama/e37251ec2aac8f6c98f75cd0fa37cd28/index.m3u8"},
    {"name": "MBC Masr Drama", "id": "MBCMasrDrama.sa", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-masr-drama/567b703c19ede6598222de81b0e4508b/index.m3u8"},
    {"name": "MBC Persia", "id": "MBCPersia.ae", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-persia/818ee8e4b592dc497608f066d825bfb4/index.m3u8"},
    {"name": "MBC Persia (720p)", "id": "MBCPersia.ae", "url": "https://hls.mbcpersia.live/hls/stream.m3u8"},
    {"name": "MBC Bollywood", "id": "MBCBollywood.ae", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-bollywood/546eb40d7dcf9a209255dd2496903764/index.m3u8"},
    {"name": "MBC Mood", "id": "MBCMood.sa", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-mood/78367bf48ccdba501d0d014a10c21031/index.m3u8"},
    {"name": "MBC FM", "id": "MBCFM.ae", "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-fm/3f36f7db6086acf058dc51681c87f8ad/index.m3u8"},
]

PREMIUM_JSON = os.path.join(os.path.dirname(__file__), "premium_channels.json")
CHECKER_PARALLEL = 30
CHECKER_TIMEOUT_MS = 15000

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read()

def run_iptv_checker(m3u_text):
    """Runs freearhey/iptv-checker (ffprobe-based) and returns the surviving m3u body."""
    if not m3u_text.strip():
        return ""
    workdir = tempfile.mkdtemp(prefix="iptv-checker-")
    infile = os.path.join(workdir, "in.m3u")
    outdir = os.path.join(workdir, "out")
    with open(infile, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n" + m3u_text)

    npx = shutil.which("npx") or "npx"
    subprocess.run(
        [npx, "--yes", "iptv-checker", infile, "-o", outdir,
         "-p", str(CHECKER_PARALLEL), "-t", str(CHECKER_TIMEOUT_MS)],
        check=True,
        shell=(os.name == "nt"),
    )

    with open(os.path.join(outdir, "online.m3u"), "r", encoding="utf-8") as f:
        online = f.read()
    shutil.rmtree(workdir, ignore_errors=True)

    lines = online.split("\n")
    if lines and lines[0].strip() == "#EXTM3U":
        lines = lines[1:]
    return "\n".join(lines).strip()

def filter_dead(text, label):
    before = text.count("#EXTINF")
    survivors = run_iptv_checker(text)
    after = survivors.count("#EXTINF")
    print(f"  {label}: {after} alive, {before - after} dead removed")
    return survivors

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
    persiana = filter_dead(persiana, "Persiana")
    p_count = persiana.count("#EXTINF")

    print("Adding MBC channels...")
    mbc_lines = []
    for ch in MBC_CHANNELS:
        mbc_lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-logo="" group-title="MBC",{ch["name"]}')
        mbc_lines.append(ch["url"])
    mbc = filter_dead("\n".join(mbc_lines), "MBC")
    m_count = mbc.count("#EXTINF")

    print("Adding Premium HD channels...")
    prem_lines = []
    if os.path.isfile(PREMIUM_JSON):
        with open(PREMIUM_JSON, "r", encoding="utf-8") as f:
            prem = json.load(f)
        for ch in prem:
            logo = ch.get("logo", "")
            tid = ch.get("tvg_id", "")
            name = ch.get("name", "")
            lo = name.lower()
            if "sport" in lo or "fox" in lo or "bein" in lo:
                grp = "Sports HD"
            elif "movie" in lo or "film" in lo or "cinema" in lo:
                grp = "Movies HD"
            elif "bbc" in lo:
                grp = "BBC HD"
            elif "mtv" in lo or "music" in lo:
                grp = "Music HD"
            elif "travel" in lo:
                grp = "Travel HD"
            elif "bloomberg" in lo or "news" in lo or "cnn" in lo:
                grp = "News HD"
            elif "document" in lo or "discovery" in lo or "nature" in lo:
                grp = "Documentary HD"
            else:
                grp = "Premium HD"
            prem_lines.append(f'#EXTINF:-1 tvg-id="{tid}" tvg-logo="{logo}" group-title="{grp}",{name}')
            prem_lines.append(ch["url"])
    premium = filter_dead("\n".join(prem_lines), "Premium HD")
    pr_count = premium.count("#EXTINF")

    print("Fetching Israel channels from idanplus...")
    israel = get_israel()
    israel = filter_dead(israel, "Israel")
    i_count = israel.count("#EXTINF")

    header = f'#EXTM3U x-tvg-url="{EPG_URLS}"\n\n'

    m3u = header
    m3u += "## --- Persiana + Iran ---\n"
    m3u += persiana + "\n\n"
    m3u += "## --- MBC ---\n"
    m3u += mbc + "\n\n"
    m3u += "## --- Premium HD ---\n"
    m3u += premium + "\n\n"
    m3u += "## --- Israel ---\n"
    m3u += israel + "\n"

    out = os.path.join(os.path.dirname(__file__), "final.m3u")
    with open(out, "w", encoding="utf-8") as f:
        f.write(m3u)

    total = p_count + m_count + pr_count + i_count
    print(f"Done: {total} channels -> {out}")

if __name__ == "__main__":
    main()
