# Sonarr Hunter - Force Sonarr to Hunt Missing Episodes

<h2 align="center">Want to Help? Click the Star in the Upper-Right Corner! ⭐</h2>

**NOTE**  
This utilizes Sonarr API Version - `5`. The Script: [sonarr-hunter.sh](sonarr-hunter.sh) 

To run via Docker

```bash
docker run -d --name sonarr-hunter \
  -e SONARR_URL="http://yoursonarr:8989" \
  -e SONARR_API_KEY="your_real_api_key" \
  -e MAX_SHOWS="1" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  admin9705/sonarr-hunter
```

**Change Log:**
- **v1**: Original code written
- **v2**: Searches for random shows that are missing at least one episode ONLY and conducts a refresh check like Radarr Hunter (basically ignores shows that are full)

<img width="900" alt="image" src="https://github.com/user-attachments/assets/f9adbd85-cda1-4f46-a4e0-5c775681baed" />

### Other Project Guide (Just FYI)

* Sister Version (Radarr): [https://github.com/plexguide/Raddar-Hunter](https://github.com/plexguide/Radarr-Hunter)<br>
* Visit: https://github.com/plexguide/Unraid_Intel-ARC_Deployment - Converts videos to AV1 Format (I've saved 325TB encoding to AV1)
* For other scripts great scripts, visit https://plexguide.com

# Sonarr Missing Episode Search Tool

## Overview

This script continually searches your Sonarr library for shows with missing episodes and automatically triggers searches for those missing episodes. It's designed to run continuously while being gentle on your indexers, helping you gradually complete your TV show collection.

## Features

- 🔄 **Continuous Operation**: Runs indefinitely until manually stopped
- 🎲 **Random Selection**: By default, selects shows randomly to distribute searches across your library
- ⏱️ **Throttled Searches**: Includes configurable delays to prevent overloading indexers
- 📊 **Status Reporting**: Provides clear feedback about what it's doing and which shows it's searching for
- 🛡️ **Error Handling**: Gracefully handles connection issues and API failures

## How It Works

1. **Initialization**: Connects to your Sonarr instance and retrieves a list of all shows
2. **Selection Process**: Randomly selects shows from your library (or sequentially if configured)
3. **Detection**: Checks if the selected show has missing episodes by comparing episode counts
4. **Search Trigger**: For shows with missing episodes, it instructs Sonarr to search for those episodes
5. **Throttling**: After finding and processing a show with missing episodes, it pauses for a configurable amount of time
6. **Cycling**: After processing the configured number of shows, it starts a new cycle, refreshing the show data

## Configuration Options

At the top of the script, you'll find these configurable options:

```bash
API_KEY="your_api_key_here"        # Your Sonarr API key
SONARR_URL="http://your.sonarr.ip:port"  # URL to your Sonarr instance
MAX_SHOWS=1                         # Shows to process before restarting cycle
SLEEP_DURATION=900                   # Seconds to wait after finding missing episodes
RANDOM_SELECTION=true               # true for random selection, false for sequential
```

## Use Cases

- **Library Completion**: Gradually fill in missing episodes of TV shows
- **New Show Setup**: Automatically find episodes for newly added shows
- **Background Service**: Run it in the background to continuously maintain your library

## How to Run (Unraid Users)

1. Install the plugin called `UserScripts`
2. Copy and paste the following script file as new script - [sonarr-hunter.sh](sonarr-hunter.sh) 
3. Ensure to set it to  `Run in the background` if your array is already running and set the schedule to  `At Startup Array`

<img width="1337" alt="image" src="https://github.com/user-attachments/assets/dbaf9864-1db9-42a5-bd0b-60b6310f9694" />

## How to Run (Non-Unraid Users)

1. Save the script to a file (e.g., `sonarr-hunter.sh`)
2. Make it executable: `chmod +x sonarr-hunter.sh`
3. Run it: `./sonarr-hunter.sh`

For continuous background operation:
- Use `screen` or `tmux`: `screen -S sonarr-hunter ./sonarr-hunter.sh`
- Or create a systemd service to run it automatically on startup

## Tips

- **First-Time Use**: Start with default settings to ensure it works with your setup
- **Adjusting Speed**: Lower the `SLEEP_DURATION` to search more frequently (be careful with indexer limits)
- **Multiple Shows**: Increase `MAX_SHOWS` if you want to search for more shows per cycle
- **System Resources**: The script uses minimal resources and can run continuously on even low-powered systems

## Troubleshooting

- **API Key Issues**: Check that your API key is correct in Sonarr settings
- **Connection Problems**: Ensure the Sonarr URL is accessible from where you're running the script
- **High Resource Usage**: If you notice high CPU usage, ensure jq is installed properly

---

This script helps automate the tedious process of finding missing episodes in your TV collection, running quietly in the background while respecting your indexers' rate limits.
