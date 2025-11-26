import os
import json
import shelve
import requests
import humanize
import time
from typing import TypedDict, Optional
from datetime import datetime

class TorrentInfo(TypedDict):
    hash: str
    name: str
    size: int
    downloaded: int
    uploaded: int
    dlspeed: int
    upspeed: int
    ratio: float
    state: str

def login_qbittorrent(base_url: str, username: str, password: str) -> Optional[requests.Session]:
    session = requests.Session()
    session.headers.update({'Referer': base_url})
    login_url = f"{base_url}/api/v2/auth/login"
    try:
        response = session.post(login_url, data={'username': username, 'password': password})
        if response.status_code == 200 and response.text == 'Ok.':
            return session
    except requests.RequestException:
        pass
    return None

def get_torrents_info(session: requests.Session, base_url: str) -> list[TorrentInfo]:
    torrents_url = f"{base_url}/api/v2/torrents/info"
    try:
        response = session.get(torrents_url)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return []

def load_previous_stats() -> dict:
    try:
        with shelve.open('torrent_stats.db') as db:
            return dict(db.get('torrents', {}))
    except Exception:
        return {}

def save_current_stats(torrents: list[TorrentInfo]):
    try:
        with shelve.open('torrent_stats.db') as db:
            stats = {t['hash']: {'uploaded': t['uploaded'], 'downloaded': t['downloaded'], 'name': t['name']} for t in torrents}
            db['torrents'] = stats
    except Exception:
        pass

def send_discord_webhook(webhook_url: str, embeds: list):
    try:
        payload = {"embeds": embeds}
        requests.post(webhook_url, json=payload)
    except Exception:
        pass

def format_torrent_stats(torrents: list[TorrentInfo], webhook_url: str):
    if not torrents:
        return
    
    previous_stats = load_previous_stats()
    
    total_downloaded = sum(t['downloaded'] for t in torrents)
    total_uploaded = sum(t['uploaded'] for t in torrents)
    total_dlspeed = sum(t['dlspeed'] for t in torrents)
    total_upspeed = sum(t['upspeed'] for t in torrents)
    
    active_count = sum(1 for t in torrents if t['state'] in ['downloading', 'uploading', 'forcedUP', 'forcedDL'])
    stalled_count = sum(1 for t in torrents if t['state'] in ['stalledUP', 'stalledDL'])
    seeding_count = sum(1 for t in torrents if t['state'] in ['uploading', 'stalledUP', 'forcedUP', 'queuedUP', 'checkingUP'])
    downloading_count = sum(1 for t in torrents if t['state'] in ['downloading', 'stalledDL', 'forcedDL', 'queuedDL', 'checkingDL', 'metaDL'])
    paused_count = sum(1 for t in torrents if 'paused' in t['state'].lower())
    
    total_uploaded_since_last = 0
    total_downloaded_since_last = 0
    new_torrents = 0
    for torrent in torrents:
        torrent_hash = torrent['hash']
        if torrent_hash in previous_stats:
            uploaded_diff = torrent['uploaded'] - previous_stats[torrent_hash]['uploaded']
            downloaded_diff = torrent['downloaded'] - previous_stats[torrent_hash].get('downloaded', 0)
            total_uploaded_since_last += uploaded_diff
            total_downloaded_since_last += downloaded_diff
        else:
            new_torrents += 1
    
    deleted_count = 0
    if previous_stats:
        current_hashes = {t['hash'] for t in torrents}
        deleted_count = sum(1 for prev_hash in previous_stats if prev_hash not in current_hashes)
    
    fields = [
        {
            "name": "Torrents",
            "value": f"Total: **{len(torrents)}**\nActive: **{active_count}** | Stalled: **{stalled_count}**",
            "inline": True
        },
        {
            "name": "Transfer",
            "value": f"Downloaded: **{humanize.naturalsize(total_downloaded, binary=True)}**\nUploaded: **{humanize.naturalsize(total_uploaded, binary=True)}**",
            "inline": True
        },
        {
            "name": "Since Last Poll",
            "value": f"**{humanize.naturalsize(total_downloaded_since_last, binary=True)}**\n⬆ **{humanize.naturalsize(total_uploaded_since_last, binary=True)}**",
            "inline": True
        },
        {
            "name": "Speed",
            "value": f"**{total_dlspeed / 1024 / 1024:.2f} MB/s**\n⬆ **{total_upspeed / 1024 / 1024:.2f} MB/s**",
            "inline": True
        }
    ]
    
    if new_torrents > 0 or deleted_count > 0:
        changes = []
        if new_torrents > 0:
            changes.append(f"New: **{new_torrents}**")
        if deleted_count > 0:
            changes.append(f"Deleted: **{deleted_count}**")
        fields.append({
            "name": "Changes",
            "value": " | ".join(changes),
            "inline": False
        })
    
    embed = {
        "title": "Torrent Stats",
        "color": 0x5865F2,
        "fields": fields,
        "timestamp": datetime.now().isoformat()
    }
    
    save_current_stats(torrents)
    send_discord_webhook(webhook_url, [embed])

def query_qbittorrent(qbitorrent_url: str, username: str, password: str, webhook_url: str):
    session = login_qbittorrent(qbitorrent_url, username, password)
    if not session:
        return
    torrents = get_torrents_info(session, qbitorrent_url)
    format_torrent_stats(torrents, webhook_url)

def main():
    qbittorrent_url = os.getenv("QBITTORRENT_URL")
    qbittorrent_username = os.getenv("QBITTORRENT_USERNAME")
    qbittorrent_password = os.getenv("QBITTORRENT_PASSWORD")
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    polling_interval = int(os.getenv("POLLING_INTERVAL", "30"))
    
    while True:
        query_qbittorrent(qbittorrent_url, qbittorrent_username, qbittorrent_password, webhook_url)
        time.sleep(polling_interval)

if __name__ == "__main__":
    main()
