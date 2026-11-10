#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
from datetime import datetime, timezone

CSV_FILE = "freetv-us-103-numeric-servers.csv"
JSON_FILE = "channels.json"
M3U_FILE = "playlist.m3u"
CATEGORY_DIR = "playlists"
EPG_FILE = "epg.xml"

REPO_RAW = "https://raw.githubusercontent.com/michaelthomas/freetv-us-repository/main"
ICON_BASE = f"{REPO_RAW}/logos"
EPG_URL = ""

def slugify(text):
    text = text.strip().replace("&", "and").replace("+", "Plus")
    text = re.sub(r"[^\w\-]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_") or "Uncategorized"

def read_csv(path):
    channels = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            channels.append({
                "number": row["Number"].strip(),
                "name": row["Channel"].strip(),
                "category": row["Category"].strip() or "Uncategorized",
                "language": row["Language"].strip(),
                "server": row["Server"].strip(),
                "numeric_address": row["Numeric-address server"].strip().lower() == "yes",
                "in_playlist": row["In repository playlist"].strip().lower() == "yes",
                "listings": row["Listings"].strip().lower() == "yes",
                "id": row["Channel ID"].strip(),
                "url": row["Link"].strip(),
            })
    return channels

def build_extinf(ch, with_logo=True, epg_url=""):
    parts = [f'tvg-id="{ch["id"]}"', f'tvg-name="{ch["name"]}"']
    if with_logo:
        parts.append(f'tvg-logo="{ICON_BASE}/{ch["id"]}.png"')
    parts.append(f'group-title="{ch["category"]}"')
    return f'#EXTINF:-1 {" ".join(parts)},{ch["name"]}'

def write_m3u(channels, path, with_logo=True, epg_url=""):
    lines = ["#EXTM3U"]
    for ch in channels:
        lines.append(build_extinf(ch, with_logo, epg_url))
        lines.append(ch["url"])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"OK {path}: {len(channels)} channels")

def write_json(channels, path):
    data = {
        "name": "FreeTV US",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_channels": len(channels),
        "categories": sorted({c["category"] for c in channels}),
        "languages": sorted({c["language"] for c in channels}),
        "playlist_url": f"{REPO_RAW}/playlist.m3u",
        "channels": channels,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"OK {path}: {len(channels)} channels")

def write_category_playlists(channels, out_dir, with_logo=True, epg_url=""):
    os.makedirs(out_dir, exist_ok=True)
    by_cat = {}
    for ch in channels:
        by_cat.setdefault(ch["category"], []).append(ch)
    for cat, chans in sorted(by_cat.items()):
        write_m3u(chans, os.path.join(out_dir, f"{slugify(cat)}.m3u"), with_logo, epg_url)
    print(f"OK {out_dir}/: {len(by_cat)} category playlists")

def write_epg(channels, path):
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S +0000")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', f'<tv generator-info-name="FreeTV US" generated="{now}">']
    for ch in channels:
        name = ch["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f'  <channel id="{ch["id"]}">')
        lines.append(f'    <display-name>{name}</display-name>')
        lines.append(f'    <icon src="{ICON_BASE}/{ch["id"]}.png"/>')
        lines.append('  </channel>')
    lines.append('</tv>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"OK {path}: {len(channels)} channels")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--category")
    p.add_argument("--epg", action="store_true")
    p.add_argument("--no-logos", action="store_true")
    args = p.parse_args()

    if not os.path.exists(CSV_FILE):
        raise SystemExit(f"CSV not found: {CSV_FILE}")

    channels = read_csv(CSV_FILE)
    with_logo = not args.no_logos

    if args.category:
        filtered = [c for c in channels if c["category"].lower() == args.category.lower()]
        write_m3u(filtered, os.path.join(CATEGORY_DIR, f"{slugify(args.category)}.m3u"), with_logo, EPG_URL)
        return

    write_json(channels, JSON_FILE)
    write_m3u(channels, M3U_FILE, with_logo, EPG_URL)
    write_category_playlists(channels, CATEGORY_DIR, with_logo, EPG_URL)
    if args.epg:
        write_epg(channels, EPG_FILE)

if __name__ == "__main__":
    main()