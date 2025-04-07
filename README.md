# Huntarr [Sonarr Edition] - Force Sonarr to Hunt Missing Shows & Upgrade Episode Qualities
 
<h2 align="center">Want to Help? Click the Star in the Upper-Right Corner! ⭐</h2>

<table>
  <tr>
    <td colspan="2"><img src="https://github.com/user-attachments/assets/34264f2e-928d-44e5-adb7-0dbd08fadfd0" width="100%"/></td>
  </tr>
</table>


**NOTE**: This utilizes Sonarr API Version - `5`. Legacy name of this program: Sonarr Hunter.

---

**Change Log:**
Visit: https://github.com/plexguide/Huntarr-Sonarr/releases/

## Table of Contents
- [Overview](#overview)
- [Related Projects](#related-projects)
- [Features](#features)
- [How It Works](#how-it-works)
- [Configuration Options](#configuration-options)
- [Web Interface](#web-interface)
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

* [Huntarr - Radarr Edition](https://github.com/plexguide/Radarr-Hunter) - Sister version for Movies
* [Huntarr - Lidarr Edition](https://github.com/plexguide/Lidarr-Hunter) - Sister version for Music
* [Huntarr - Readarr Edition](https://github.com/plexguide/Huntarr-Readarr) - Sister version for Books
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
- 📦 **Modular Design**: Modern codebase with separated concerns for easier maintenance
- 🌐 **Web Interface**: Real-time log viewer with day/night mode
- 🔮 **Future Episode Skipping**: Skip processing episodes with future air dates
- 💾 **Reduced Disk Activity**: Option to skip series refresh before processing

## Indexers Approving of Huntarr:
* https://ninjacentral.co.za

## How It Works

1. **Initialization**: Connects to your Sonarr instance and analyzes your library
2. **Missing Episodes**: 
   - Identifies shows with missing episodes
   - Randomly selects shows to process (up to configurable limit)
   - Refreshes metadata (optional) and triggers searches
   - Skips episodes with future air dates (configurable)
3. **Quality Upgrades**:
   - Finds episodes that don't meet your quality cutoff settings
   - Processes them in configurable batches
   - Uses smart pagination to handle large libraries
   - Skips episodes with future air dates (configurable)
4. **State Management**:
   - Tracks which shows and episodes have been processed
   - Automatically resets this tracking after a configurable time period
5. **Repeat Cycle**: Waits for a configurable period before starting the next cycle

<table>
  <tr>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/d758b9ae-ecef-4056-ba4e-a7fe363bd182" width="100%"/>
      <p align="center"><em>Missing Episodes Demo</em></p>
    </td>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/923033d5-fb86-4777-952f-638d8503f776" width="100%"/>
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

| Variable                      | Description                                                              | Default    |
|-------------------------------|-----------------------------------------------------------------------|---------------|
| `API_KEY`                     | Your Sonarr API key                                                      | Required   |
| `API_URL`                     | URL to your Sonarr instance                                              | Required   |
| `API_TIMEOUT`                 | Timeout in seconds for API requests to Sonarr                            | 60         |
| `MONITORED_ONLY`              | Only process monitored shows/episodes                                    | true       |
| `HUNT_MISSING_SHOWS`          | Maximum missing shows to process per cycle                               | 1          |
| `HUNT_UPGRADE_EPISODES`       | Maximum upgrade episodes to process per cycle                            | 5          |
| `SLEEP_DURATION`              | Seconds to wait after completing a cycle (900 = 15 minutes)              | 900        |
| `RANDOM_SELECTION`            | Use random selection (`true`) or sequential (`false`)                    | true       |
| `STATE_RESET_INTERVAL_HOURS`  | Hours which the processed state files reset (168=1 week, 0=never reset)  | 168        |
| `DEBUG_MODE`                  | Enable detailed debug logging (`true` or `false`)                        | false      |
| `ENABLE_WEB_UI`               | Enable or disable the web interface (`true` or `false`)                  | true       |
| `SKIP_FUTURE_EPISODES`        | Skip processing episodes with future air dates (`true` or `false`)       | true       |
| `SKIP_SERIES_REFRESH`         | Skip refreshing series metadata before processing (`true` or `false`)    | false      |

### Advanced Options (Optional)

| Variable                      | Description                                                              | Default    |
|-------------------------------|-----------------------------------------------------------------------|---------------|
| `COMMAND_WAIT_DELAY`          | Delay in seconds between checking for command status                     | 1          |
| `COMMAND_WAIT_ATTEMPTS`       | Number of attempts to check for command completion before giving up      | 600        |
| `MINIMUM_DOWNLOAD_QUEUE_SIZE` | Minimum number of items in the download queue before starting a hunt     | -1         |

### Detailed Configuration Explanation

- **API_TIMEOUT**
  - Sets the maximum number of seconds to wait for Sonarr API responses before timing out.
  - This is particularly important when working with large libraries or when checking for many quality upgrades.
  - If you experience timeout errors (especially during the "Checking for Quality Upgrades" phase), increase this value.
  - For libraries with thousands of episodes needing quality upgrades, values of 90-120 seconds may be necessary.
  - Default is 60 seconds, which works well for most medium-sized libraries.

- **HUNT_MISSING_SHOWS**  
  - Sets the maximum number of missing shows to process in each cycle.  
  - Once this limit is reached, the script stops processing further missing shows until the next cycle.
  - Set to `0` to disable missing show processing completely.

- **HUNT_UPGRADE_EPISODES**  
  - Sets the maximum number of upgrade episodes to process in each cycle.  
  - When this limit is reached, the upgrade portion of the cycle stops.
  - Set to `0` to disable quality upgrade processing completely.

- **RANDOM_SELECTION**
  - When `true`, selects shows and episodes randomly, which helps distribute searches across your library.
  - When `false`, processes items sequentially, which can be more predictable and methodical.

- **STATE_RESET_INTERVAL_HOURS**  
  - Controls how often the script "forgets" which items it has already processed.  
  - The script records the IDs of missing shows and upgrade episodes that have been processed.  
  - When the age of these records exceeds the number of hours set by this variable, the records are cleared automatically.  
  - This reset allows the script to re-check items that were previously processed.
  - Setting this to `0` will disable the reset functionality entirely - processed items will be remembered indefinitely.
  - Default is 168 hours (one week) - meaning the script will start fresh weekly.

- **DEBUG_MODE**
  - When set to `true`, the script will output detailed debugging information about API responses and internal operations.
  - Useful for troubleshooting issues but can make logs verbose.

- **ENABLE_WEB_UI**
  - When set to `true`, the web interface will be enabled on port 8988.
  - When set to `false`, the web interface will not start, saving resources.
  - Default is `true` for convenient monitoring.

- **SKIP_FUTURE_EPISODES**
  - When set to `true`, the script will skip processing episodes with future air dates.
  - This helps avoid unnecessary searches for content that isn't available yet.
  - Works for both missing episodes and quality upgrade processing.
  - Default is `true` to optimize search efficiency.

- **SKIP_SERIES_REFRESH**
  - When set to `true`, the script will skip refreshing series metadata before searching.
  - This can significantly reduce disk activity on your Sonarr server.
  - Default is `false` to maintain compatibility with previous behavior.
  - Set to `true` if you notice excessive disk activity during Huntarr cycles.

- **COMMAND_WAIT_DELAY**
  - Certain operations like refreshing and searching happen asynchronously.  
  - This is the delay in seconds between checking the status of these operations for completion.
  - By checking for these to complete before proceeding we can ensure we do not overload the command queue.
  - Operations like refreshing update show metadata so this ensures those actions are fully completed before additional operations are performed.

- **COMMAND_WAIT_ATTEMPTS**
  - The number of attempts to wait for an operation to complete before giving up.  If a command times out the operation will be considered failed.

- **MINIMUM_DOWNLOAD_QUEUE_SIZE**
  - The minimum number of items in the download queue before a new hunt is initiated.  For example if set to `5` then a new hunt will only start when there are 5 or less items marked as `downloading` in the queue.
  - This helps prevent overwhelming the queue with too many download requests at once and avoids creating a massive backlog of downloads.
  - Set to `-1` to disable this check.

## Web Interface

Huntarr-Sonarr includes a real-time log viewer web interface that allows you to monitor its operation directly from your browser.

### Features

- **Real-time Log Updates**: Logs refresh automatically every second
- **Day/Night Mode**: Toggle between light and dark themes
- **Color-coded Log Entries**: Different log levels are displayed in different colors
- **Auto-scrolling**: Automatically scrolls to the latest log entries
- **Connection Status**: Shows whether the connection to the log stream is active

### How to Access

The web interface is available on port 8988. Simply navigate to:

```
http://YOUR_SERVER_IP:8988
```

Or if you're accessing it locally:

```
http://localhost:8988
```

### Port Configuration Explained

When running with Docker, you need to map the container's internal port to a port on your host system. The format is `HOST_PORT:CONTAINER_PORT`.

For example:
- `8988:8988` means "map port 8988 from the host to port 8988 in the container"

If you want to use a different port on your host (e.g., 9000), you would use:
- `9000:8988` means "map port 9000 from the host to port 8988 in the container"

You would then access the web interface at `http://YOUR_SERVER_IP:9000`

### Enabling/Disabling the Web UI

The web interface can be enabled or disabled using the `ENABLE_WEB_UI` environment variable:

- `ENABLE_WEB_UI=true` - Enable the web interface (default)
- `ENABLE_WEB_UI=false` - Disable the web interface

If you disable the web interface, you don't need to expose the port in your Docker configuration.

---

## Installation Methods

### Docker Run

The simplest way to run Huntarr is via Docker:

```bash
docker run -d --name huntarr-sonarr \
  --restart always \
  -p 8988:8988 \  # Can be removed if ENABLE_WEB_UI=false
  -e API_KEY="your-api-key" \
  -e API_URL="http://your-sonarr-address:8989" \
  -e API_TIMEOUT="60" \
  -e MONITORED_ONLY="true" \
  -e HUNT_MISSING_SHOWS="1" \
  -e HUNT_UPGRADE_EPISODES="5" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  -e STATE_RESET_INTERVAL_HOURS="168" \
  -e DEBUG_MODE="false" \
  -e ENABLE_WEB_UI="true" \
  -e SKIP_FUTURE_EPISODES="true" \
  -e SKIP_SERIES_REFRESH="false" \
  huntarr/4sonarr:latest
  
  # Optional advanced settings
  # -e COMMAND_WAIT_DELAY="1" \
  # -e COMMAND_WAIT_ATTEMPTS="600" \
  # -e MINIMUM_DOWNLOAD_QUEUE_SIZE="-1" \
```

To check on the status of the program, you can use the web interface at http://YOUR_SERVER_IP:8988 or check the logs with:
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
    ports:
      - "8988:8988"  # Can be removed if ENABLE_WEB_UI=false
    environment:
      API_KEY: "your-api-key"
      API_URL: "http://your-sonarr-address:8989"
      API_TIMEOUT: "60"
      MONITORED_ONLY: "true"
      HUNT_MISSING_SHOWS: "1"
      HUNT_UPGRADE_EPISODES: "5"
      SLEEP_DURATION: "900"
      RANDOM_SELECTION: "true"
      STATE_RESET_INTERVAL_HOURS: "168"
      DEBUG_MODE: "false"
      ENABLE_WEB_UI: "true"
      SKIP_FUTURE_EPISODES: "true"
      SKIP_SERIES_REFRESH: "false"
      
      # Optional advanced settings
      # COMMAND_WAIT_DELAY: "1"
      # COMMAND_WAIT_ATTEMPTS: "600"
      # MINIMUM_DOWNLOAD_QUEUE_SIZE: "-1"
```

Then run:

```bash
docker-compose up -d huntarr-sonarr
```

### Unraid Users

Run this from Command Line in Unraid:

```bash
docker run -d --name huntarr-sonarr \
  --restart always \
  -p 8988:8988 \  # Can be removed if ENABLE_WEB_UI=false
  -e API_KEY="your-api-key" \
  -e API_URL="http://your-sonarr-address:8989" \
  -e API_TIMEOUT="60" \
  -e MONITORED_ONLY="true" \
  -e HUNT_MISSING_SHOWS="1" \
  -e HUNT_UPGRADE_EPISODES="5" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  -e STATE_RESET_INTERVAL_HOURS="168" \
  -e DEBUG_MODE="false" \
  -e ENABLE_WEB_UI="true" \
  -e SKIP_FUTURE_EPISODES="true" \
  -e SKIP_SERIES_REFRESH="false" \
  huntarr/4sonarr:latest
  
  # Optional advanced settings
  # -e COMMAND_WAIT_DELAY="1" \
  # -e COMMAND_WAIT_ATTEMPTS="600" \
  # -e MINIMUM_DOWNLOAD_QUEUE_SIZE="-1" \
```

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
Environment="API_TIMEOUT=60"
Environment="MONITORED_ONLY=true"
Environment="HUNT_MISSING_SHOWS=1"
Environment="HUNT_UPGRADE_EPISODES=5"
Environment="SLEEP_DURATION=900"
Environment="RANDOM_SELECTION=true"
Environment="STATE_RESET_INTERVAL_HOURS=168"
Environment="DEBUG_MODE=false"
Environment="ENABLE_WEB_UI=true"
Environment="SKIP_FUTURE_EPISODES=true"
Environment="SKIP_SERIES_REFRESH=false"
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
- **Real-time Monitoring**: Use the web interface to see what's happening at any time
- **Disk Usage Optimization**: Skip refreshing metadata to reduce disk wear and tear
- **Efficient Searching**: Skip processing episodes with future air dates to save resources

## Tips

- **First-Time Use**: Start with default settings to ensure it works with your setup
- **Adjusting Speed**: Lower the `SLEEP_DURATION` to search more frequently (be careful with indexer limits)
- **Batch Size Control**: Adjust `HUNT_MISSING_SHOWS` and `HUNT_UPGRADE_EPISODES` based on your indexer's rate limits
- **Monitored Status**: Set `MONITORED_ONLY=false` if you want to download all missing episodes regardless of monitored status
- **System Resources**: The script uses minimal resources and can run continuously on even low-powered systems
- **Web Interface**: Use the web interface to monitor progress instead of checking Docker logs
- **Port Conflicts**: If port 8988 is already in use, map to a different host port (e.g., `-p 9000:8988`)
- **Disable Web UI**: Set `ENABLE_WEB_UI=false` if you don't need the interface to save resources
- **Debugging Issues**: Enable `DEBUG_MODE=true` temporarily to see detailed logs when troubleshooting
- **Hard Drive Saving**: Enable `SKIP_SERIES_REFRESH=true` to reduce disk activity
- **Search Efficiency**: Keep `SKIP_FUTURE_EPISODES=true` to avoid searching for unavailable content

## Troubleshooting

- **API Key Issues**: Check that your API key is correct in Sonarr settings
- **Connection Problems**: Ensure the Sonarr URL is accessible from where you're running the script
- **Command Failures**: If search commands fail, try using the Sonarr UI to verify what commands are available in your version
- **Web Interface Not Loading**: Make sure port 8988 is exposed in your Docker configuration and not blocked by a firewall
- **Logs**: Check the container logs with `docker logs huntarr-sonarr` if running in Docker
- **Debug Mode**: Enable `DEBUG_MODE=true` to see detailed API responses and process flow
- **State Files**: The script stores state in `/tmp/huntarr-state/` - if something seems stuck, you can try deleting these files
- **Excessive Disk Activity**: If you notice high disk usage, try enabling `SKIP_SERIES_REFRESH=true`

---

This script helps automate the tedious process of finding missing episodes and quality upgrades in your TV collection, running quietly in the background while respecting your indexers' rate limits.

---

Thanks to: 

[IntensiveCareCub](https://www.reddit.com/user/IntensiveCareCub/) for the Hunter to Huntarr idea!