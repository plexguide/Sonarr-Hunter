# Sonarr Hunter - Force Sonarr to Hunt Missing Episodes

<h2 align="center">Want to Help? Click the Star in the Upper-Right Corner! ⭐</h2>

![image](https://github.com/user-attachments/assets/34264f2e-928d-44e5-adb7-0dbd08fadfd0)

**NOTE**: This utilizes Sonarr API Version - `5`. The Script: [sonarr-hunter.sh](sonarr-hunter.sh)

## Table of Contents
- [Overview](#overview)
- [Related Projects](#related-projects)
- [Features](#features)
- [How It Works](#how-it-works)
- [Configuration Options](#configuration-options)
- [Installation Methods](#installation-methods)
  - [Docker Run](#docker-run)
  - [Docker Compose](#docker-compose)
  - [Unraid Users](#unraid-users)
  - [SystemD Service](#systemd-service)
- [Use Cases](#use-cases)
- [Tips](#tips)
- [Troubleshooting](#troubleshooting)

## Overview

This script continually searches your Sonarr library for shows with missing episodes and automatically triggers searches for those missing episodes. It's designed to run continuously while being gentle on your indexers, helping you gradually complete your TV show collection.

## Related Projects

* [Radarr Hunter](https://github.com/plexguide/Radarr-Hunter) - Sister version for movies
* [Lidarr Hunter](https://github.com/plexguide/Lidarr-Hunter) - Sister version for music
* [Unraid Intel ARC Deployment](https://github.com/plexguide/Unraid_Intel-ARC_Deployment) - Convert videos to AV1 Format (I've saved 325TB encoding to AV1)
* Visit [PlexGuide](https://plexguide.com) for more great scripts

## Features

- 🔄 **Continuous Operation**: Runs indefinitely until manually stopped
- 🎯 **Direct Missing Episode Targeting**: Directly identifies and processes only shows with missing episodes
- 🎲 **Random Selection**: By default, selects shows randomly to distribute searches across your library
- ⏱️ **Throttled Searches**: Includes configurable delays to prevent overloading indexers
- 📊 **Status Reporting**: Provides clear feedback about what it's doing and which shows it's searching for
- 🛡️ **Error Handling**: Gracefully handles connection issues and API failures

## How It Works

1. **Initialization**: Connects to your Sonarr instance and retrieves a list of shows with missing episodes
2. **Selection Process**: Randomly selects a show with missing episodes from the filtered list
3. **Refresh**: Refreshes the metadata for the selected show
4. **Search Trigger**: Uses the MissingEpisodeSearch command to instruct Sonarr to search for missing episodes
5. **Throttling**: After processing a show, it pauses for a configurable amount of time
6. **Cycling**: After processing the configured number of shows, it starts a new cycle, refreshing the data

## Configuration Options

The following environment variables can be configured:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Your Sonarr API key | Required |
| `API_URL` | URL to your Sonarr instance | Required |
| `MONITORED_ONLY` | Only process monitored shows/episodes | true |
| `MAX_SHOWS` | Shows to process before restarting cycle | 1 |
| `SLEEP_DURATION` | Seconds to wait after processing a show (900=15min) | 900 |
| `RANDOM_SELECTION` | Use random selection (`true`) or sequential (`false`) | true |

## Installation Methods

### Docker Run

The simplest way to run Sonarr Hunter is via Docker:

```bash
docker run -d --name sonarr-hunter \
  --restart always \
  -e API_KEY="your-api-key" \
  -e API_URL="http://your-sonarr-address:8989" \
  -e MONITORED_ONLY="true" \
  -e MAX_SHOWS="1" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  admin9705/sonarr-hunter:latest
```

### Docker Compose

For those who prefer Docker Compose, add this to your `docker-compose.yml` file:

```yaml
version: '3'
services:
  sonarr-hunter:
    container_name: sonarr-hunter
    image: admin9705/sonarr-hunter:latest
    restart: always
    environment:
      - API_KEY=your-api-key
      - API_URL=http://sonarr:8989
      - MONITORED_ONLY=true
      - MAX_SHOWS=1
      - SLEEP_DURATION=900
      - RANDOM_SELECTION=true
```

Then run:

```bash
docker-compose up -d sonarr-hunter
```

To check on the status of the program, you should see new files downloading or you can type:
```bash
docker logs sonarr-hunter
```

### Unraid Users

1. Install the plugin called `UserScripts`
2. Copy and paste the following script file as a new script - [sonarr-hunter.sh](sonarr-hunter.sh) 
3. Ensure to set it to `Run in the background` if your array is already running and set the schedule to `At Startup Array`

### SystemD Service

For a more permanent installation on Linux systems using SystemD:

1. Save the script to `/usr/local/bin/sonarr-hunter.sh`
2. Make it executable: `chmod +x /usr/local/bin/sonarr-hunter.sh`
3. Create a systemd service file at `/etc/systemd/system/sonarr-hunter.service`:

```ini
[Unit]
Description=Sonarr Hunter Service
After=network.target sonarr.service

[Service]
Type=simple
User=your-username
Environment="API_KEY=your-api-key"
Environment="API_URL=http://localhost:8989"
Environment="MONITORED_ONLY=true"
Environment="MAX_SHOWS=1"
Environment="SLEEP_DURATION=900"
Environment="RANDOM_SELECTION=true"
ExecStart=/usr/local/bin/sonarr-hunter.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. Enable and start the service:

```bash
sudo systemctl enable sonarr-hunter
sudo systemctl start sonarr-hunter
```

## Use Cases

- **Library Completion**: Gradually fill in missing episodes of TV shows
- **New Show Setup**: Automatically find episodes for newly added shows
- **Background Service**: Run it in the background to continuously maintain your library

## Tips

- **First-Time Use**: Start with default settings to ensure it works with your setup
- **Adjusting Speed**: Lower the `SLEEP_DURATION` to search more frequently (be careful with indexer limits)
- **Multiple Shows**: Increase `MAX_SHOWS` if you want to search for more shows per cycle
- **Monitored Status**: Set `MONITORED_ONLY=false` if you want to download all missing episodes regardless of monitored status
- **System Resources**: The script uses minimal resources and can run continuously on even low-powered systems

## Troubleshooting

- **API Key Issues**: Check that your API key is correct in Sonarr settings
- **Connection Problems**: Ensure the Sonarr URL is accessible from where you're running the script
- **Command Failures**: If search commands fail, try using the Sonarr UI to verify what commands are available in your version
- **Logs**: Check the container logs with `docker logs sonarr-hunter` if running in Docker

---

**Change Log:**
- **v1**: Original code written
- **v2**: Optimized search
- **v3**: Variable names changed for docker optimization
- **v4**: Added monitored only tag

---

This script helps automate the tedious process of finding missing episodes in your TV collection, running quietly in the background while respecting your indexers' rate limits.
