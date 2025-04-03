#!/usr/bin/env bash

# ---------------------------
# Main Configuration Variables
# ---------------------------

API_KEY=${API_KEY:-"your-api-key"}
API_URL=${API_URL:-"http://your-radarr-address:7878"}

# Maximum number of missing movies to process per cycle
MAX_MISSING=${MAX_MISSING:-1}

# Maximum number of upgrade movies to process per cycle
MAX_UPGRADES=${MAX_UPGRADES:-5}

# Sleep duration in seconds after completing one full cycle (default 15 minutes)
SLEEP_DURATION=${SLEEP_DURATION:-900}

# New variable: Reset processed state file after this many hours (default 168 hours)
# Note: Set to 0 to disable automatic reset (never forget processed items)
STATE_RESET_INTERVAL_HOURS=${STATE_RESET_INTERVAL_HOURS:-168}

# ---------------------------
# Miscellaneous Configuration
# ---------------------------
# Set to true to pick items randomly, false to go in order
RANDOM_SELECTION=${RANDOM_SELECTION:-true}

# If MONITORED_ONLY is "true", only process missing or upgrade movies from monitored movies
MONITORED_ONLY=${MONITORED_ONLY:-true}

# SEARCH_TYPE controls what we search for:
# - "missing" => Only find movies that are missing
# - "upgrade" => Only find movies that don't meet quality cutoff
# - "both"    => Do missing movies first, then upgrade movies
SEARCH_TYPE=${SEARCH_TYPE:-"both"}

# Enable debug mode to see API responses
DEBUG_MODE=${DEBUG_MODE:-false}

# ---------------------------
# State Tracking Setup
# ---------------------------
# These state files persist IDs for processed missing movies and upgrade movies.
# They will be automatically cleared if older than the reset interval.
STATE_DIR="/tmp/huntarr-radarr-state"
mkdir -p "$STATE_DIR"
PROCESSED_MISSING_FILE="$STATE_DIR/processed_missing_ids.txt"
PROCESSED_UPGRADE_FILE="$STATE_DIR/processed_upgrade_ids.txt"
touch "$PROCESSED_MISSING_FILE" "$PROCESSED_UPGRADE_FILE"

# ---------------------------
# State Reset Check
# ---------------------------
# Check and reset state files if they are older than the configured reset interval.
# Skip this check if STATE_RESET_INTERVAL_HOURS is set to 0 (disabled)
if [ "$STATE_RESET_INTERVAL_HOURS" -gt 0 ]; then
    current_time=$(date +%s)
    missing_age=$(( current_time - $(stat -c %Y "$PROCESSED_MISSING_FILE") ))
    upgrade_age=$(( current_time - $(stat -c %Y "$PROCESSED_UPGRADE_FILE") ))
    reset_interval_seconds=$(( STATE_RESET_INTERVAL_HOURS * 3600 ))
    
    if [ "$missing_age" -ge "$reset_interval_seconds" ] || [ "$upgrade_age" -ge "$reset_interval_seconds" ]; then
        echo "Resetting processed state files (older than ${STATE_RESET_INTERVAL_HOURS} hours)."
        > "$PROCESSED_MISSING_FILE"
        > "$PROCESSED_UPGRADE_FILE"
    fi
else
    echo "State reset is disabled (STATE_RESET_INTERVAL_HOURS=0). Processed items will be remembered indefinitely."
fi

# ---------------------------
# Debug Helper
# ---------------------------
debug_log() {
  if [ "$DEBUG_MODE" = "true" ]; then
    echo "[DEBUG] $1"
    if [ -n "$2" ]; then
      echo "$2" | head -n 20
    fi
  fi
}

# ---------------------------
# Internal Calculation (Do Not Modify)
# ---------------------------
# Convert hours to seconds for internal use.
# If STATE_RESET_INTERVAL_HOURS is 0, set a very large number effectively disabling resets
if [ "$STATE_RESET_INTERVAL_HOURS" -gt 0 ]; then
    STATE_RESET_INTERVAL_SECONDS=$(( STATE_RESET_INTERVAL_HOURS * 3600 ))
else
    # Set to a very large value (100 years in seconds) when disabled
    STATE_RESET_INTERVAL_SECONDS=3155760000
fi

# ---------------------------
# Helper: Radarr API Calls
# ---------------------------

debug_log "API KEY: $API_KEY"
debug_log "API URL $API_URL"

get_movies() {
  curl -s -H "X-Api-Key: $API_KEY" "$API_URL/api/v3/movie"
}

refresh_movie() {
  local movie_id="$1"
  curl -s -X POST \
       -H "X-Api-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d "{\"name\":\"RefreshMovie\",\"movieIds\":[$movie_id]}" \
       "$API_URL/api/v3/command"
}

missing_movie_search() {
  local movie_id="$1"
  curl -s -X POST \
       -H "X-Api-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d "{\"name\":\"MoviesSearch\",\"movieIds\":[$movie_id]}" \
       "$API_URL/api/v3/command"
}

rescan_movie() {
  local movie_id="$1"
  curl -s -X POST \
       -H "X-Api-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d "{\"name\":\"RescanMovie\",\"movieIds\":[$movie_id]}" \
       "$API_URL/api/v3/command"
}

get_cutoff_unmet() {
  local page="${1:-1}"
  curl -s -H "X-Api-Key: $API_KEY" \
       "$API_URL/api/v3/movie/movie" | \
       jq '[.[] | select(.qualityCutoffNotMet == true)]'
}

get_cutoff_unmet_count() {
  local response
  response=$(curl -s -H "X-Api-Key: $API_KEY" "$API_URL/api/v3/movie" | \
              jq '[.[] | select(.qualityCutoffNotMet == true)] | length')
  echo "$response"
}

# ---------------------------
# 1) Missing Movies Logic (Persistent)
# ---------------------------
process_missing_movies() {
  echo "=== Checking for Missing Movies ==="
  local movies_json
  movies_json=$(get_movies)
  debug_log "Raw movies API response first 100 chars:" "$(echo "$movies_json" | head -c 100)"
  if [ -z "$movies_json" ]; then
    echo "ERROR: Unable to retrieve movie data from Radarr. Retrying in 60s..."
    sleep 60
    return
  fi

  local missing_json
  if [ "$MONITORED_ONLY" = "true" ]; then
    echo "MONITORED_ONLY=true => only monitored movies without files."
    missing_json=$(echo "$movies_json" | jq '[.[] | select(.monitored == true and .hasFile == false)]')
  else
    echo "MONITORED_ONLY=false => all movies without files."
    missing_json=$(echo "$movies_json" | jq '[.[] | select(.hasFile == false)]')
  fi

  local total_missing
  total_missing=$(echo "$missing_json" | jq 'length')
  debug_log "Total missing movies: $total_missing"
  debug_log "First missing movie (if any):" "$(echo "$missing_json" | jq '.[0]')"
  if [ "$total_missing" -eq 0 ]; then
    echo "No missing movies found."
    return
  fi

  local processed_missing_ids
  mapfile -t processed_missing_ids < "$PROCESSED_MISSING_FILE"

  echo "Found $total_missing movie(s) with missing files."
  local movies_processed=0
  local indices
  if [ "$RANDOM_SELECTION" = "true" ]; then
    indices=($(seq 0 $((total_missing - 1)) | shuf))
  else
    indices=($(seq 0 $((total_missing - 1))))
  fi

  for index in "${indices[@]}"; do
    if [ "$MAX_MISSING" -gt 0 ] && [ "$movies_processed" -ge "$MAX_MISSING" ]; then
      break
    fi

    local movie
    movie=$(echo "$missing_json" | jq ".[$index]")
    local movie_id
    movie_id=$(echo "$movie" | jq '.id')
    if echo "${processed_missing_ids[@]}" | grep -qw "$movie_id"; then
      continue
    fi

    local movie_title
    movie_title=$(echo "$movie" | jq -r '.title')
    local movie_year
    movie_year=$(echo "$movie" | jq -r '.year')

    echo "Processing missing movie \"$movie_title ($movie_year)\" (ID: $movie_id)."
    echo " - Refreshing movie..."
    local refresh_cmd
    refresh_cmd=$(refresh_movie "$movie_id")
    local refresh_id
    refresh_id=$(echo "$refresh_cmd" | jq '.id // empty')
    if [ -z "$refresh_id" ]; then
      echo "WARNING: Refresh command failed for $movie_title. Skipping."
      sleep 10
      continue
    fi

    echo "Refresh command accepted (ID: $refresh_id). Waiting 5s..."
    sleep 5

    echo " - Searching for \"$movie_title\"..."
    local search_cmd
    search_cmd=$(missing_movie_search "$movie_id")
    local search_id
    search_id=$(echo "$search_cmd" | jq '.id // empty')
    if [ -n "$search_id" ]; then
      echo "Search command accepted (ID: $search_id)."
    else
      echo "WARNING: Movie search failed."
    fi

    echo " - Rescanning movie folder..."
    local rescan_cmd
    rescan_cmd=$(rescan_movie "$movie_id")
    local rescan_id
    rescan_id=$(echo "$rescan_cmd" | jq '.id // empty')
    if [ -n "$rescan_id" ]; then
      echo "Rescan command accepted (ID: $rescan_id)."
    else
      echo "WARNING: Rescan command not available or failed."
    fi

    echo "$movie_id" >> "$PROCESSED_MISSING_FILE"
    movies_processed=$((movies_processed + 1))
    echo "Processed $movies_processed/$MAX_MISSING missing movies this cycle."
  done
}

# ---------------------------
# 2) Upgrade Logic (Cutoff Unmet, Persistent)
# ---------------------------
process_cutoff_upgrades() {
  echo "=== Checking for Quality Upgrades (Cutoff Unmet) ==="
  
  local cutoff_json
  cutoff_json=$(get_cutoff_unmet)
  if [ -z "$cutoff_json" ]; then
    echo "ERROR: Unable to retrieve cutoff unmet data from Radarr. Retrying in 60s..."
    sleep 60
    return
  fi
  
  local total_upgrades
  total_upgrades=$(echo "$cutoff_json" | jq 'length')
  
  if [ "$total_upgrades" -eq 0 ]; then
    echo "No movies found that need quality upgrades."
    return
  fi

  echo "Found $total_upgrades movies that need quality upgrades."
  local movies_processed=0
  local processed_movie_ids
  mapfile -t processed_movie_ids < "$PROCESSED_UPGRADE_FILE"

  local indices
  if [ "$RANDOM_SELECTION" = "true" ]; then
    indices=($(seq 0 $((total_upgrades - 1)) | shuf))
  else
    indices=($(seq 0 $((total_upgrades - 1))))
  fi

  for index in "${indices[@]}"; do
    if [ "$MAX_UPGRADES" -gt 0 ] && [ "$movies_processed" -ge "$MAX_UPGRADES" ]; then
      break
    fi

    local movie
    movie=$(echo "$cutoff_json" | jq ".[$index]")
    local movie_id
    movie_id=$(echo "$movie" | jq '.id')
    
    if echo "${processed_movie_ids[@]}" | grep -qw "$movie_id"; then
      continue
    fi

    local movie_title
    movie_title=$(echo "$movie" | jq -r '.title')
    local movie_year
    movie_year=$(echo "$movie" | jq -r '.year')
    local quality_profile
    quality_profile=$(echo "$movie" | jq -r '.qualityProfileId')

    if [ "$MONITORED_ONLY" = "true" ]; then
      local movie_monitored
      movie_monitored=$(echo "$movie" | jq '.monitored')
      if [ "$movie_monitored" != "true" ]; then
        echo "Skipping unmonitored movie: $movie_title ($movie_year)"
        continue
      fi
    fi

    echo "Processing quality upgrade for \"$movie_title ($movie_year)\" (ID: $movie_id)"
    echo " - Refreshing movie information..."
    local refresh_cmd
    refresh_cmd=$(refresh_movie "$movie_id")
    local refresh_id
    refresh_id=$(echo "$refresh_cmd" | jq '.id // empty')
    if [ -z "$refresh_id" ]; then
      echo "WARNING: Refresh command failed. Skipping this movie."
      sleep 10
      continue
    fi
    echo "Refresh command accepted (ID: $refresh_id). Waiting 5s..."
    sleep 5

    echo " - Searching for quality upgrade..."
    local search_cmd
    search_cmd=$(missing_movie_search "$movie_id")
    local search_id
    search_id=$(echo "$search_cmd" | jq '.id // empty')
    if [ -n "$search_id" ]; then
      echo "Search command accepted (ID: $search_id)."
      echo "$movie_id" >> "$PROCESSED_UPGRADE_FILE"
      processed_movie_ids+=("$movie_id")
      movies_processed=$((movies_processed + 1))
      echo "Processed $movies_processed/$MAX_UPGRADES upgrade movies this cycle."
    else
      echo "WARNING: Search command failed for movie ID $movie_id."
      sleep 10
    fi
  done

  echo "Completed processing $movies_processed upgrade movies for this cycle."
  local processed_count
  processed_count=$(wc -l < "$PROCESSED_UPGRADE_FILE")
  if [ "$processed_count" -gt 1000 ]; then
    echo "Processed upgrade movies list is getting large. Truncating to last 500 entries."
    tail -n 500 "$PROCESSED_UPGRADE_FILE" > "${PROCESSED_UPGRADE_FILE}.tmp"
    mv "${PROCESSED_UPGRADE_FILE}.tmp" "$PROCESSED_UPGRADE_FILE"
  fi
}

# ---------------------------
# Main Loop
# ---------------------------
while true; do
  case "$SEARCH_TYPE" in
    missing)
      process_missing_movies
      ;;
    upgrade)
      process_cutoff_upgrades
      ;;
    both)
      process_missing_movies
      process_cutoff_upgrades
      ;;
    *)
      echo "Unknown SEARCH_TYPE=$SEARCH_TYPE. Use 'missing','upgrade','both'."
      ;;
  esac

  # Calculate minutes remaining until the state files are reset
  # Skip this if reset is disabled (STATE_RESET_INTERVAL_HOURS=0)
  if [ "$STATE_RESET_INTERVAL_HOURS" -gt 0 ]; then
    current_time=$(date +%s)
    # Find the minimum remaining time among the two state files
    missing_remaining=$(( STATE_RESET_INTERVAL_SECONDS - ( current_time - $(stat -c %Y "$PROCESSED_MISSING_FILE") ) ))
    upgrade_remaining=$(( STATE_RESET_INTERVAL_SECONDS - ( current_time - $(stat -c %Y "$PROCESSED_UPGRADE_FILE") ) ))
    if [ "$missing_remaining" -gt "$upgrade_remaining" ]; then
      remaining_seconds=$upgrade_remaining
    else
      remaining_seconds=$missing_remaining
    fi
    remaining_minutes=$(( remaining_seconds / 60 ))
    echo "Cycle complete. Waiting $SLEEP_DURATION seconds before next cycle..."
    echo "State reset will occur in approximately $remaining_minutes minutes."
  else
    echo "Cycle complete. Waiting $SLEEP_DURATION seconds before next cycle..."
    echo "State reset is disabled. Processed items will be remembered indefinitely."
  fi
  
  echo "Like the tool? Donate toward my daughter's college fund via donate.plex.one and make her day!"
  sleep "$SLEEP_DURATION"
done
