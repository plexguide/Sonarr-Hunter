# Huntarr [Radarr Edition] - Force Radarr to Hunt Missing Movies & Upgrade Movie Qualities

<h2 align="center">Want to Help? Click the Star in the Upper-Right Corner! ⭐</h2>

<table>
  <tr>
    <td colspan="2"><img src="https://github.com/user-attachments/assets/21721557-01a6-462a-b7c3-54bbcd8514c4" width="100%"/></td>
  </tr>
</table>

**NOTE**: This utilizes Radarr API Version - `3`. The Script: [huntarr.sh](huntarr.sh)

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

This script continually searches your Radarr library for missing movies and movies that need quality upgrades. It automatically triggers searches for both missing movies and movies below your quality cutoff. It's designed to run continuously while being gentle on your indexers, helping you gradually complete your movie collection with the best available quality.

## Related Projects

* [Huntarr - Sonarr Edition](https://github.com/plexguide/Sonarr-Hunter) - Sister version for TV shows
* [Huntarr - Lidarr Edition](https://github.com/plexguide/Lidarr-Hunter) - Sister version for music
* [Unraid Intel ARC Deployment](https://github.com/plexguide/Unraid_Intel-ARC_Deployment) - Convert videos to AV1 Format (I've saved 325TB encoding to AV1)
* Visit [PlexGuide](https://plexguide.com) for more great scripts

## PayPal Donations – Building My Daughter's Future

My 12-year-old daughter loves singing, dancing, and exploring STEM. She's an A-B honor roll student with big dreams for the future. Any donation you make will go directly toward her college fund, helping her turn those dreams into reality. Thank you for your support!

[![Donate with PayPal button](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate?hosted_button_id=58AYJ68VVMGSC)

## Features

- 🔄 **Continuous Operation**: Runs indefinitely until manually stopped
- 🎯 **Dual Targeting System**: Targets both missing movies and quality upgrades
- 🎲 **Random Selection**: By default, selects movies randomly to distribute searches across your library
- ⏱️ **Throttled Searches**: Includes configurable delays to prevent overloading indexers
- 📊 **Status Reporting**: Provides clear feedback about what it's doing and which movies it's searching for
- 🛡️ **Error Handling**: Gracefully handles connection issues and API failures
- 🔁 **State Tracking**: Remembers which movies have been processed to avoid duplicate searches
- ⚙️ **Configurable Reset Timer**: Automatically resets search history after a configurable period

## How It Works

1. **Initialization**: Connects to your Radarr instance and analyzes your library
2. **Missing Movies**: 
   - Identifies movies without files
   - Randomly selects movies to process (up to configurable limit)
   - Refreshes metadata and triggers searches
3. **Quality Upgrades**:
   - Finds movies that don't meet your quality cutoff settings
   - Processes them in configurable batches
   - Uses smart selection to distribute searches
4. **State Management**:
   - Tracks which movies have been processed
   - Automatically resets this tracking after a configurable time period
5. **Repeat Cycle**: Waits for a configurable period before starting the next cycle

<table>
  <tr>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/dbaf9864-1db9-42a5-bd0b-60b6310f9694" width="100%"/>
      <p align="center"><em>Missing Movies Demo</em></p>
    </td>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/dbaf9864-1db9-42a5-bd0b-60b6310f9694" width="100%"/>
      <p align="center"><em>Quality Upgrade Demo</em></p>
    </td>
  </tr>
  <tr>
    <td colspan="2">
      <img src="https://github.com/user-attachments/assets/dbaf9864-1db9-42a5-bd0b-60b6310f9694" width="100%"/>
      <p align="center"><em>State Management System</em></p>
    </td>
  </tr>
</table>

## Configuration Options

The following environment variables can be configured:

| Variable                     | Description                                                              | Default    |
|------------------------------|-----------------------------------------------------------------------|---------------|
| `API_KEY`                    | Your Radarr API key                                                      | Required   |
| `API_URL`                    | URL to your Radarr instance                                              | Required   |
| `MONITORED_ONLY`             | Only process monitored movies                                            | true       |
| `SEARCH_TYPE`                | Which search to perform: `"missing"`, `"upgrade"`, or `"both"`           | both       |
| `MAX_MISSING`                | Maximum missing movies to process per cycle                              | 1          |
| `MAX_UPGRADES`               | Maximum upgrade movies to process per cycle                              | 5          |
| `SLEEP_DURATION`             | Seconds to wait after completing a cycle (900 = 15 minutes)              | 900        |
| `RANDOM_SELECTION`           | Use random selection (`true`) or sequential (`false`)                    | true       |
| `STATE_RESET_INTERVAL_HOURS` | Hours which the processed state files reset (168=1 week, 0=never reset)  | 168        |
| `DEBUG_MODE`                 | Enable detailed debug logging (`true` or `false`)                        | false      |

### Detailed Configuration Explanation

- **SEARCH_TYPE**  
  - Determines which type of search the script performs.  
  - Options:  
    - `"missing"`: Only processes missing movies (movies that haven't been downloaded yet).  
    - `"upgrade"`: Only processes movies that need quality upgrades (do not meet the quality cutoff).  
    - `"both"`: First processes missing movies and then processes upgrade movies in one cycle.

- **MAX_MISSING**  
  - Sets the maximum number of missing movies to process in each cycle.  
  - Once this limit is reached, the script stops processing further missing movies until the next cycle.

- **MAX_UPGRADES**  
  - Sets the maximum number of upgrade movies to process in each cycle.  
  - When this limit is reached, the upgrade portion of the cycle stops and the script waits for the next cycle.

- **RANDOM_SELECTION**
  - When `true`, selects movies randomly, which helps distribute searches across your library.
  - When `false`, processes movies sequentially, which can be more predictable and methodical.

- **STATE_RESET_INTERVAL_HOURS**  
  - Controls how often the script "forgets" which movies it has already processed.  
  - The script records the IDs of missing movies and upgrade movies that have been processed.  
  - When the age of these records exceeds the number of hours set by this variable, the records are cleared automatically.  
  - This reset allows the script to re-check movies that were previously processed, so if there are changes (such as improved quality), they can be processed again.  
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
docker run -d --name huntarr-radarr \
  --restart always \
  -e API_KEY="your-api-key" \
  -e API_URL="http://your-radarr-address:7878" \
  -e MONITORED_ONLY="true" \
  -e SEARCH_TYPE="both" \
  -e MAX_MISSING="1" \
  -e MAX_UPGRADES="5" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  -e STATE_RESET_INTERVAL_HOURS="168" \
  -e DEBUG_MODE="false" \
  huntarr/4radarr:latest
```

To check on the status of the program, you should see new files downloading or you can type:
```bash
docker logs huntarr-radarr
```

### Docker Compose

For those who prefer Docker Compose, add this to your `docker-compose.yml` file:

```yaml
version: "3.8"
services:
  huntarr-radarr:
    image: huntarr/4radarr:latest
    container_name: huntarr-radarr
    restart: always
    environment:
      API_KEY: "your-api-key"
      API_URL: "http://your-radarr-address:7878"
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
docker-compose up -d huntarr-radarr
```

To check on the status of the program, you should see new files downloading or you can type:
```bash
docker logs huntarr-radarr
```

### Unraid Users

1. Install the plugin called `UserScripts`
2. Copy and paste the following script file as a new script - [huntarr.sh](huntarr.sh) 
3. Ensure to set it to `Run in the background` if your array is already running and set the schedule to `At Startup Array`
4. Update the variables at the top of the script to match your configuration

<table>
  <tr>
    <td colspan="2">
      <img src="https://github.com/user-attachments/assets/dbaf9864-1db9-42a5-bd0b-60b6310f9694" width="100%"/>
      <p align="center"><em>User Scripts - Unraid</em></p>
    </td>
  </tr>
</table>

### SystemD Service

For a more permanent installation on Linux systems using SystemD:

1. Save the script to `/usr/local/bin/huntarr.sh`
2. Make it executable: `chmod +x /usr/local/bin/huntarr.sh`
3. Create a systemd service file at `/etc/systemd/system/huntarr.service`:

```ini
[Unit]
Description=Huntarr Service
After=network.target radarr.service

[Service]
Type=simple
User=your-username
Environment="API_KEY=your-api-key"
Environment="API_URL=http://localhost:7878"
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

- **Library Completion**: Gradually fill in missing movies in your collection
- **Quality Improvement**: Automatically upgrade movie quality as better versions become available
- **New Movie Setup**: Automatically find newly added movies
- **Background Service**: Run it in the background to continuously maintain your library
- **Smart Rotation**: With state tracking, ensures all content gets attention over time

## Tips

- **First-Time Use**: Start with default settings to ensure it works with your setup
- **Adjusting Speed**: Lower the `SLEEP_DURATION` to search more frequently (be careful with indexer limits)
- **Focus on Missing or Upgrades**: Use the `SEARCH_TYPE` setting to focus on what matters to you
- **Batch Size Control**: Adjust `MAX_MISSING` and `MAX_UPGRADES` based on your indexer's rate limits
- **Monitored Status**: Set `MONITORED_ONLY=false` if you want to download all missing movies regardless of monitored status
- **System Resources**: The script uses minimal resources and can run continuously on even low-powered systems
- **Debugging Issues**: Enable `DEBUG_MODE=true` temporarily to see detailed logs when troubleshooting

## Troubleshooting

- **API Key Issues**: Check that your API key is correct in Radarr settings
- **Connection Problems**: Ensure the Radarr URL is accessible from where you're running the script
- **Command Failures**: If search commands fail, try using the Radarr UI to verify what commands are available in your version
- **Logs**: Check the container logs with `docker logs huntarr-radarr` if running in Docker
- **Debug Mode**: Enable `DEBUG_MODE=true` to see detailed API responses and process flow
- **State Files**: The script stores state in `/tmp/huntarr-radarr-state/` - if something seems stuck, you can try deleting these files

---

**Change Log:**
- **v1**: Original code written
- **v2**: Added dual targeting for both missing and quality upgrade movies
- **v3**: Added state tracking to prevent duplicate searches
- **v4**: Implemented configurable state reset timer
- **v5**: Added debug mode and improved error handling
- **v6**: Enhanced random selection mode for better distribution
- **v7**: Renamed from "Radarr Hunter" to "Huntarr [Radarr Edition]"

---

This script helps automate the tedious process of finding missing movies and quality upgrades in your collection, running quietly in the background while respecting your indexers' rate limits.

---

Thanks to: 

[IntensiveCareCub](https://www.reddit.com/user/IntensiveCareCub/) for the Hunter to Huntarr idea!
