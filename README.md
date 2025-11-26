# qBittorrent Daily Report

Monitor qBittorrent torrents and send statistics to Discord via webhook.

## Setup

1. Copy `docker-compose.yml` and set environment variables:
   - `QBITTORRENT_URL` - Your qBittorrent WebUI URL
   - `QBITTORRENT_USERNAME` - WebUI username
   - `QBITTORRENT_PASSWORD` - WebUI password
   - `DISCORD_WEBHOOK_URL` - Discord webhook URL
   - `POLLING_INTERVAL` - Seconds between checks (default: 30)

2. Run with Docker:
   ```bash
   docker compose up -d
   ```

## What it does

- Polls qBittorrent every configurable period
- Tracks torrent statistics and changes over time
- Sends Discord notifications showing:
  - Total torrents (active/stalled counts)
  - Transfer totals and speeds
  - Upload/download since last poll
  - New and deleted torrents
