# Huntarr [Sonarr Edition] - Force Sonarr to Hunt Missing Shows & Upgrade Episode Qualities

<h2 align="center">Want to Help? Click the Star in the Upper-Right Corner! ⭐</h2>

<table>
  <tr>
    <td colspan="2"><img src="https://github.com/user-attachments/assets/7c0d98f4-3ee3-4d60-be93-0ec4e92d7227" width="100%"/></td>
  </tr>
</table>

<table>
  <tr>
    <td colspan="2"><img src="https://github.com/user-attachments/assets/34264f2e-928d-44e5-adb7-0dbd08fadfd0" width="100%"/></td>
  </tr>
</table>


**NOTE**: This utilizes Sonarr API Version - `5`. The Script: [huntarr.sh](huntarr.sh)

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

This script continually searches your Sonarr library for shows with missing episodes and episodes that need quality upgrades. It automatically triggers searches for both missing episodes and episodes below your quality cutoff. It's designed to run continuously while being gentle on your indexers, helping you gradually complete your TV show collection with the best available quality.

## Related Projects

* [Huntarr - Radarr Edition](https://github.com/plexguide/Radarr-Hunter) - Sister version for movies
* [Huntarr - Lidarr Edition](https://github.com/plexguide/Lidarr-Hunter) - Sister version for music
* [Unraid Intel ARC Deployment](https://github.com/plexguide/Unraid_Intel-ARC_Deployment) - Convert videos to AV1 Format (I've saved 325TB encoding to AV1)
* Visit [PlexGuide](https://plexguide.com) for more great scripts

## PayPal Donations – Building My Daughter's Future

My 12-year-old daughter is passionate about singing, dancing, and exploring STEM. She consistently earns A-B honors and dreams of a bright future. Every donation goes directly into her college fund, helping turn those dreams into reality. Thank you for your generous support!

[![Donate with PayPal button](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate?hosted_button_id=58AYJ68VVMGSC)

## Features

- 🔄 **Continuous Operation**: Runs indefinitely until manually stopped
- 🎯 **Dual Targeting System**: Targets both missing episodes and quality upgrades
- 🎲 **Random Selection**: By default, selects shows and episodes randomly to distribute searches across your library
- ⏱️ **Throttled Searches**: Includes configurable delays to prevent overloading indexers
- 📊 **Status Reporting**: Provides clear feedback about what it's doing and which shows it's searching for
- 🛡️ **Error Handling**: Gracefully handles connection issues and API failures
- 🔁 **State Tracking**: Remembers which shows and episodes have been processed to avoid duplicate searches
- ⚙️ **Configurable Reset Timer**: Automatically resets search history after a configurable period

## How It Works

1. **Initialization**: Connects to your Sonarr instance and analyzes your library
2. **Missing Episodes**: 
   - Identifies shows with missing episodes
   - Randomly selects shows to process (up to configurable limit)
   - Refreshes metadata and triggers searches
3. **Quality Upgrades**:
   - Finds episodes that don't meet your quality cutoff settings
   - Processes them in configurable batches
   - Uses smart pagination to handle large libraries
4. **State Management**:
   - Tracks which shows and episodes have been processed
   - Automatically resets this tracking after a configurable time period
5. **Repeat Cycle**: Waits for a configurable period before starting the next cycle

<table>
  <tr>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/6a9dd459-db84-42bc-9392-27491d2ae1c8" width="100%"/>
      <p align="center"><em>Missing Episodes Demo</em></p>
    </td>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/db502745-adb2-47e5-95e5-51d2ea54aa59" width="100%"/>
      <p align="center"><em>Quality Upgrade Demo</em></p>
    </td>
  </tr>
  <tr>
    <td colspan="2">
      <img src="https://github.com/user-attachments/assets/3e95f6d5-4a96-4bb8-a5b9-1d7b871ff94a" width="100%"/>
      <p align="center"><em>State Management System</em></p>
    </td>
  </tr>
</table>

## Configuration Options

The following environment variables can be configured:

| Variable                     | Description                                                              | Default    |
|------------------------------|-----------------------------------------------------------------------|---------------|
| `API_KEY`                    | Your Sonarr API key                                                      | Required   |
| `API_URL`                    | URL to your Sonarr instance                                              | Required   |
| `MONITORED_ONLY`             | Only process monitored shows/episodes                                    | true       |
| `SEARCH_TYPE`                | Which search to perform: `"missing"`, `"upgrade"`, or `"both"`           | both       |
| `MAX_MISSING`                | Maximum missing shows to process per cycle                               | 1          |
| `MAX_UPGRADES`               | Maximum upgrade episodes to process per cycle                            | 5          |
| `SLEEP_DURATION`             | Seconds to wait after completing a cycle (900 = 15 minutes)              | 900        |
| `RANDOM_SELECTION`           | Use random selection (`true`) or sequential (`false`)                    | true       |
| `STATE_RESET_INTERVAL_HOURS` | Hours which the processed state files reset (168=1 week, 0=never reset)  | 168        |
| `DEBUG_MODE`                 | Enable detailed debug logging (`true` or `false`)                        | false      |

### Detailed Configuration Explanation

- **SEARCH_TYPE**  
  - Determines which type of search the script performs.  
  - Options:  
    - `"missing"`: Only processes missing shows (episodes that haven't been downloaded yet).  
    - `"upgrade"`: Only processes episodes that need quality upgrades (do not meet the quality cutoff).  
    - `"both"`: First processes missing shows and then processes upgrade episodes in one cycle.

- **MAX_MISSING**  
  - Sets the maximum number of missing shows to process in each cycle.  
  - Once this limit is reached, the script stops processing further missing shows until the next cycle.

- **MAX_UPGRADES**  
  - Sets the maximum number of upgrade episodes to process in each cycle.  
  - When this limit is reached, the upgrade portion of the cycle stops and the script waits for the next cycle.

- **RANDOM_SELECTION**
  - When `true`, selects shows and episodes randomly, which helps distribute searches across your library.
  - When `false`, processes items sequentially, which can be more predictable and methodical.

- **STATE_RESET_INTERVAL_HOURS**  
  - Controls how often the script "forgets" which items it has already processed.  
  - The script records the IDs of missing shows and upgrade episodes that have been processed.  
  - When the age of these records exceeds the number of hours set by this variable, the records are cleared automatically.  
  - This reset allows the script to re-check items that were previously processed, so if there are changes (such as improved quality or new episodes), they can be processed again.  
  - Setting this to `0` will disable the reset functionality entirely - processed items will be remembered indefinitely.
  - Default is 168 hours (one week) - meaning the script will start fresh and re-check everything weekly.

- **DEBUG_MODE**
  - When set to `true`, the script will output detailed debugging information about API responses and internal operations.
  - Useful for troubleshooting issues but can make logs verbose.

---

## Installation Methods

### Docker Run

The simplest way to run Huntarr is via Docker:

```bash
docker run -d --name huntarr-sonarr \
  --restart always \
  -e API_KEY="your-api-key" \
  -e API_URL="http://your-sonarr-address:8989" \
  -e MONITORED_ONLY="true" \
  -e SEARCH_TYPE="both" \
  -e MAX_MISSING="1" \
  -e MAX_UPGRADES="5" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  -e STATE_RESET_INTERVAL_HOURS="168" \
  -e DEBUG_MODE="false" \
  huntarr/4sonarr:latest
```

To check on the status of the program, you should see new files downloading or you can type:
```bash
docker logs huntarr-sonarr
```

### Docker Compose

For those who prefer Docker Compose, add this to your `docker-compose.yml` file:

```yaml
version: "3.8"
services:
  huntarr-sonarr:
    image: huntarr/4sonarr:latest
    container_name: huntarr-sonarr
    restart: always
    environment:
      API_KEY: "your-api-key"
      API_URL: "http://your-sonarr-address:8989"
      MONITORED_ONLY: "true"
      SEARCH_TYPE: "both"
      MAX_MISSING: "1"
      MAX_UPGRADES: "5"
      SLEEP_DURATION: "900"
      RANDOM_SELECTION: "true"
      STATE_RESET_INTERVAL_HOURS: "168"
      DEBUG_MODE: "false"
```

Then run:

```bash
docker-compose up -d huntarr-sonarr
```

To check on the status of the program, you should see new files downloading or you can type:
```bash
docker logs huntarr-sonarr
```

### Unraid Users

Run this from Command Line in Unraid. This will eventually be pushed to the Unraid App Store

docker run -d --name huntarr-sonarr \
  --restart always \
  -e API_KEY="your-api-key" \
  -e API_URL="http://your-sonarr-address:8989" \
  -e MONITORED_ONLY="true" \
  -e SEARCH_TYPE="both" \
  -e MAX_MISSING="1" \
  -e MAX_UPGRADES="5" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  -e STATE_RESET_INTERVAL_HOURS="168" \
  -e DEBUG_MODE="false" \
  huntarr/4sonarr:latest

### SystemD Service

For a more permanent installation on Linux systems using SystemD:

1. Save the script to `/usr/local/bin/huntarr.sh`
2. Make it executable: `chmod +x /usr/local/bin/huntarr.sh`
3. Create a systemd service file at `/etc/systemd/system/huntarr.service`:

```ini
[Unit]
Description=Huntarr Service
After=network.target sonarr.service

[Service]
Type=simple
User=your-username
Environment="API_KEY=your-api-key"
Environment="API_URL=http://localhost:8989"
Environment="MONITORED_ONLY=true"
Environment="SEARCH_TYPE=both"
Environment="MAX_MISSING=1"
Environment="MAX_UPGRADES=5"
Environment="SLEEP_DURATION=900"
Environment="RANDOM_SELECTION=true"
Environment="STATE_RESET_INTERVAL_HOURS=168"
Environment="DEBUG_MODE=false"
ExecStart=/usr/local/bin/huntarr.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. Enable and start the service:

```bash
sudo systemctl enable huntarr
sudo systemctl start huntarr
```

## Use Cases

- **Library Completion**: Gradually fill in missing episodes of TV shows
- **Quality Improvement**: Automatically upgrade episode quality as better versions become available
- **New Show Setup**: Automatically find episodes for newly added shows
- **Background Service**: Run it in the background to continuously maintain your library
- **Smart Rotation**: With state tracking, ensures all content gets attention over time

## Tips

- **First-Time Use**: Start with default settings to ensure it works with your setup
- **Adjusting Speed**: Lower the `SLEEP_DURATION` to search more frequently (be careful with indexer limits)
- **Focus on Missing or Upgrades**: Use the `SEARCH_TYPE` setting to focus on what matters to you
- **Batch Size Control**: Adjust `MAX_MISSING` and `MAX_UPGRADES` based on your indexer's rate limits
- **Monitored Status**: Set `MONITORED_ONLY=false` if you want to download all missing episodes regardless of monitored status
- **System Resources**: The script uses minimal resources and can run continuously on even low-powered systems
- **Debugging Issues**: Enable `DEBUG_MODE=true` temporarily to see detailed logs when troubleshooting

## Troubleshooting

- **API Key Issues**: Check that your API key is correct in Sonarr settings
- **Connection Problems**: Ensure the Sonarr URL is accessible from where you're running the script
- **Command Failures**: If search commands fail, try using the Sonarr UI to verify what commands are available in your version
- **Logs**: Check the container logs with `docker logs huntarr-sonarr` if running in Docker
- **Debug Mode**: Enable `DEBUG_MODE=true` to see detailed API responses and process flow
- **State Files**: The script stores state in `/tmp/huntarr-sonarr-state/` - if something seems stuck, you can try deleting these files

---

**Change Log:**
- **v1**: Original code written
- **v2**: Optimized search
- **v3**: Variable names changed for docker optimization
- **v4**: Added monitored only tag
- **v5**: Added quality upgrade functionality to find episodes below cutoff quality
- **v6**: Added state tracking to prevent duplicate searches
- **v7**: Implemented configurable state reset timer
- **v8**: Added debug mode and improved error handling
- **v9**: Enhanced random selection mode for better distribution
- **v10**: Renamed from "Sonarr Hunter" to "Huntarr"

---

This script helps automate the tedious process of finding missing episodes and quality upgrades in your TV collection, running quietly in the background while respecting your indexers' rate limits.

---

Thanks to: 

[IntensiveCareCub](https://www.reddit.com/user/IntensiveCareCub/) for the Hunter to Huntarr idea!
