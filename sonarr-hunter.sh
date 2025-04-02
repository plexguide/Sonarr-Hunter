#!/usr/bin/env bash

# ---------------------------
# Main Configuration Variables
# ---------------------------

API_KEY=${API_KEY:-"your-api-key"}
API_URL=${API_URL:-"http://your-sonarr-address:8989"}

# Maximum number of missing shows to process per cycle
MAX_MISSING=${MAX_MISSING:-1}

# Maximum number of upgrade episodes to process per cycle
MAX_UPGRADES=${MAX_UPGRADES:-5}

# Sleep duration in seconds after completing one full cycle (default 15 minutes)
SLEEP_DURATION=${SLEEP_DURATION:-900}

# New variable: Reset processed state file after this many hours (default 168 hours)
STATE_RESET_INTERVAL_HOURS=${STATE_RESET_INTERVAL_HOURS:-168}

# ---------------------------
# Miscellaneous Configuration
# ---------------------------
# Set to true to pick items randomly, false to go in order
RANDOM_SELECTION=${RANDOM_SELECTION:-true}

# If MONITORED_ONLY is "true", only process missing or upgrade episodes from monitored shows
MONITORED_ONLY=${MONITORED_ONLY:-true}

# SEARCH_TYPE controls what we search for:
# - "missing" => Only find shows with missing episodes
# - "upgrade" => Only find episodes that don't meet quality cutoff
# - "both"    => Do missing shows first, then upgrade episodes
SEARCH_TYPE=${SEARCH_TYPE:-"both"}

# Enable debug mode to see API responses
DEBUG_MODE=${DEBUG_MODE:-false}

# ---------------------------
# State Tracking Setup
# ---------------------------
# These state files persist IDs for processed missing shows and upgrade episodes.
# They will be automatically cleared if older than the reset interval.
STATE_DIR="/tmp/sonarr-hunter-state"
mkdir -p "$STATE_DIR"
PROCESSED_MISSING_FILE="$STATE_DIR/processed_missing_ids.txt"
PROCESSED_UPGRADE_FILE="$STATE_DIR/processed_upgrade_ids.txt"
touch "$PROCESSED_MISSING_FILE" "$PROCESSED_UPGRADE_FILE"

# ---------------------------
# State Reset Check
# ---------------------------
# Check and reset state files if they are older than the configured reset interval.
current_time=$(date +%s)
missing_age=$(( current_time - $(stat -c %Y "$PROCESSED_MISSING_FILE") ))
upgrade_age=$(( current_time - $(stat -c %Y "$PROCESSED_UPGRADE_FILE") ))
if [ "$missing_age" -ge "$(( STATE_RESET_INTERVAL_HOURS * 3600 ))" ] || [ "$upgrade_age" -ge "$(( STATE_RESET_INTERVAL_HOURS * 3600 ))" ]; then
    echo "Resetting processed state files (older than ${STATE_RESET_INTERVAL_HOURS} hours)."
    > "$PROCESSED_MISSING_FILE"
    > "$PROCESSED_UPGRADE_FILE"
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
STATE_RESET_INTERVAL_SECONDS=$(( STATE_RESET_INTERVAL_HOURS * 3600 ))

# ---------------------------
# Helper: Sonarr API Calls
# ---------------------------
get_series() {
  curl -s -H "X-Api-Key: $API_KEY" "$API_URL/api/v3/series"
}

refresh_series() {
  local series_id="$1"
  curl -s -X POST \
       -H "X-Api-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d "{\"name\":\"RefreshSeries\",\"seriesId\":$series_id}" \
       "$API_URL/api/v3/command"
}

missing_episode_search() {
  local series_id="$1"
  curl -s -X POST \
       -H "X-Api-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d "{\"name\":\"MissingEpisodeSearch\",\"seriesId\":$series_id}" \
       "$API_URL/api/v3/command"
}

episode_search_series() {
  local series_id="$1"
  curl -s -X POST \
       -H "X-Api-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d "{\"name\":\"EpisodeSearch\",\"seriesId\":$series_id}" \
       "$API_URL/api/v3/command"
}

episode_search_episodes() {
  local episode_ids="$1"
  curl -s -X POST \
       -H "X-Api-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d "{\"name\":\"EpisodeSearch\",\"episodeIds\":$episode_ids}" \
       "$API_URL/api/v3/command"
}

get_cutoff_unmet() {
  local page="${1:-1}"
  curl -s -H "X-Api-Key: $API_KEY" \
       "$API_URL/api/v3/wanted/cutoff?sortKey=airDateUtc&sortDirection=descending&includeSeriesInformation=true&page=$page&pageSize=200"
}

get_cutoff_unmet_total_pages() {
  local response
  response=$(curl -s -H "X-Api-Key: $API_KEY" "$API_URL/api/v3/wanted/cutoff?page=1&pageSize=1")
  if echo "$response" | jq -e '.totalRecords' > /dev/null 2>&1; then
    local total_records
    total_records=$(echo "$response" | jq '.totalRecords')
    if [ -z "$total_records" ] || [ "$total_records" = "null" ] || ! [[ "$total_records" =~ ^[0-9]+$ ]]; then
      echo "1"
    else
      local total_pages
      total_pages=$(( (total_records + 199) / 200 ))
      [ "$total_pages" -lt 1 ] && echo "1" || echo "$total_pages"
    fi
  else
    echo "1"
  fi
}

# ---------------------------
# 1) Missing Episodes Logic (Persistent)
# ---------------------------
process_missing_episodes() {
  echo "=== Checking for Missing Episodes ==="
  local shows_json
  shows_json=$(get_series)
  debug_log "Raw series API response first 100 chars:" "$(echo "$shows_json" | head -c 100)"
  if [ -z "$shows_json" ]; then
    echo "ERROR: Unable to retrieve series data from Sonarr. Retrying in 60s..."
    sleep 60
    return
  fi

  local incomplete_json
  if [ "$MONITORED_ONLY" = "true" ]; then
    echo "MONITORED_ONLY=true => only monitored shows with missing episodes."
    incomplete_json=$(echo "$shows_json" | jq '[.[] | select(.monitored == true and has("statistics") and .statistics.episodeCount > .statistics.episodeFileCount)]')
  else
    echo "MONITORED_ONLY=false => all shows with missing episodes."
    incomplete_json=$(echo "$shows_json" | jq '[.[] | select(has("statistics") and .statistics.episodeCount > .statistics.episodeFileCount)]')
  fi

  local total_incomplete
  total_incomplete=$(echo "$incomplete_json" | jq 'length')
  debug_log "Total incomplete shows: $total_incomplete"
  debug_log "First incomplete show (if any):" "$(echo "$incomplete_json" | jq '.[0]')"
  if [ "$total_incomplete" -eq 0 ]; then
    echo "No shows with missing episodes found."
    return
  fi

  local processed_missing_ids
  mapfile -t processed_missing_ids < "$PROCESSED_MISSING_FILE"

  echo "Found $total_incomplete show(s) with missing episodes."
  local shows_processed=0
  local indices
  if [ "$RANDOM_SELECTION" = "true" ]; then
    indices=($(seq 0 $((total_incomplete - 1)) | shuf))
  else
    indices=($(seq 0 $((total_incomplete - 1))))
  fi

  for index in "${indices[@]}"; do
    if [ "$MAX_MISSING" -gt 0 ] && [ "$shows_processed" -ge "$MAX_MISSING" ]; then
      break
    fi

    local show
    show=$(echo "$incomplete_json" | jq ".[$index]")
    local show_id
    show_id=$(echo "$show" | jq '.id')
    if echo "${processed_missing_ids[@]}" | grep -qw "$show_id"; then
      continue
    fi

    local show_title
    show_title=$(echo "$show" | jq -r '.title')
    local ep_count
    ep_count=$(echo "$show" | jq '.statistics.episodeCount')
    local ep_file_count
    ep_file_count=$(echo "$show" | jq '.statistics.episodeFileCount')
    local missing
    missing=$((ep_count - ep_file_count))

    echo "Processing missing episodes for \"$show_title\" ($missing missing)."
    echo " - Refreshing series (ID: $show_id)..."
    local refresh_cmd
    refresh_cmd=$(refresh_series "$show_id")
    local refresh_id
    refresh_id=$(echo "$refresh_cmd" | jq '.id // empty')
    if [ -z "$refresh_id" ]; then
      echo "WARNING: Refresh command failed for $show_title. Skipping."
      sleep 10
      continue
    fi

    echo "Refresh command accepted (ID: $refresh_id). Waiting 5s..."
    sleep 5

    echo " - MissingEpisodeSearch for \"$show_title\"..."
    local search_cmd
    search_cmd=$(missing_episode_search "$show_id")
    local search_id
    search_id=$(echo "$search_cmd" | jq '.id // empty')
    if [ -n "$search_id" ]; then
      echo "Search command accepted (ID: $search_id)."
    else
      echo "WARNING: MissingEpisodeSearch failed. Attempting fallback EpisodeSearch..."
      local fallback_cmd
      fallback_cmd=$(episode_search_series "$show_id")
      local fallback_id
      fallback_id=$(echo "$fallback_cmd" | jq '.id // empty')
      [ -n "$fallback_id" ] && echo "Fallback EpisodeSearch accepted (ID: $fallback_id)."
    fi

    echo "$show_id" >> "$PROCESSED_MISSING_FILE"
    shows_processed=$((shows_processed + 1))
    echo "Processed $shows_processed/$MAX_MISSING missing shows this cycle."
  done
}

# ---------------------------
# 2) Upgrade Logic (Cutoff Unmet, Persistent)
# ---------------------------
process_cutoff_upgrades() {
  echo "=== Checking for Quality Upgrades (Cutoff Unmet) ==="
  local total_pages
  total_pages=$(get_cutoff_unmet_total_pages)
  if [ "$total_pages" -eq 0 ]; then
    echo "No episodes found that need quality upgrades."
    return
  fi

  echo "Found $total_pages total pages of episodes that need quality upgrades."
  local episodes_processed=0
  local processed_episode_ids
  mapfile -t processed_episode_ids < "$PROCESSED_UPGRADE_FILE"

  while [ "$episodes_processed" -lt "$MAX_UPGRADES" ] || [ "$MAX_UPGRADES" -eq 0 ]; do
    local page
    if [ "$RANDOM_SELECTION" = "true" ] && [ "$total_pages" -gt 1 ]; then
      page=$((RANDOM % total_pages + 1))
    else
      page=1
    fi

    echo "Retrieving cutoff-unmet episodes (page=$page of $total_pages)..."
    local cutoff_json
    cutoff_json=$(get_cutoff_unmet "$page")
    if ! echo "$cutoff_json" | jq empty 2>/dev/null; then
      echo "ERROR: Invalid JSON response on page $page. Trying another page."
      if [ "$RANDOM_SELECTION" = "false" ]; then
        page=$((page + 1))
        [ "$page" -gt "$total_pages" ] && break
      fi
      continue
    fi

    local episodes
    if echo "$cutoff_json" | jq -e '.records' >/dev/null 2>&1; then
      episodes=$(echo "$cutoff_json" | jq '.records')
    else
      echo "WARNING: 'records' field missing on page $page."
      if [ "$RANDOM_SELECTION" = "false" ]; then
        page=$((page + 1))
        [ "$page" -gt "$total_pages" ] && break
      fi
      continue
    fi

    local total_eps
    total_eps=$(echo "$episodes" | jq '. | length')
    if [ -z "$total_eps" ] || [ "$total_eps" = "null" ] || ! [[ "$total_eps" =~ ^[0-9]+$ ]]; then
      echo "Invalid episode count on page $page."
      if [ "$RANDOM_SELECTION" = "false" ]; then
        page=$((page + 1))
        [ "$page" -gt "$total_pages" ] && break
      fi
      continue
    fi

    if [ "$total_eps" -eq 0 ]; then
      echo "No episodes found on page $page."
      if [ "$RANDOM_SELECTION" = "false" ]; then
        page=$((page + 1))
        [ "$page" -gt "$total_pages" ] && break
      fi
      continue
    fi

    echo "Found $total_eps episodes on page $page that need quality upgrades."
    local -a page_indices
    if [ "$RANDOM_SELECTION" = "true" ]; then
      for ((i=0; i<total_eps; i++)); do
        page_indices[$i]=$i
      done
      for ((i=total_eps-1; i>0; i--)); do
        j=$((RANDOM % (i+1)))
        temp=${page_indices[$i]}
        page_indices[$i]=${page_indices[$j]}
        page_indices[$j]=$temp
      done
    else
      for ((i=0; i<total_eps; i++)); do
        page_indices[$i]=$i
      done
    fi

    for index in "${page_indices[@]}"; do
      if [ "$MAX_UPGRADES" -gt 0 ] && [ "$episodes_processed" -ge "$MAX_UPGRADES" ]; then
        break
      fi

      local episode
      episode=$(echo "$episodes" | jq ".[$index]")
      local episode_id
      episode_id=$(echo "$episode" | jq '.id')
      if echo "${processed_episode_ids[@]}" | grep -qw "$episode_id"; then
        echo "Episode ID $episode_id already processed. Skipping."
        continue
      fi

      local series_id
      series_id=$(echo "$episode" | jq '.seriesId')
      local season_num
      season_num=$(echo "$episode" | jq '.seasonNumber')
      local ep_num
      ep_num=$(echo "$episode" | jq '.episodeNumber')
      local title
      title=$(echo "$episode" | jq -r '.title')

      local series_title
      if echo "$episode" | jq -e '.seriesTitle' >/dev/null 2>&1; then
        series_title=$(echo "$episode" | jq -r '.seriesTitle')
      else
        local series_json
        series_json=$(curl -s -H "X-Api-Key: $API_KEY" "$API_URL/api/v3/series/$series_id")
        series_title=$(echo "$series_json" | jq -r '.title')
      fi

      echo "Processing upgrade for \"$series_title\" - S${season_num}E${ep_num} - \"$title\" (Episode ID: $episode_id)"
      if [ "$MONITORED_ONLY" = "true" ]; then
        local ep_monitored
        ep_monitored=$(echo "$episode" | jq '.monitored')
        local series_monitored
        if echo "$episode" | jq -e '.series.monitored' >/dev/null 2>&1; then
          series_monitored=$(echo "$episode" | jq '.series.monitored')
        else
          local series_json
          series_json=$(curl -s -H "X-Api-Key: $API_KEY" "$API_URL/api/v3/series/$series_id")
          series_monitored=$(echo "$series_json" | jq '.monitored')
        fi
        if [ "$ep_monitored" != "true" ] || [ "$series_monitored" != "true" ]; then
          echo "Skipping unmonitored episode or series."
          continue
        fi
      fi

      echo " - Refreshing series information..."
      local refresh_cmd
      refresh_cmd=$(refresh_series "$series_id")
      local refresh_id
      refresh_id=$(echo "$refresh_cmd" | jq '.id // empty')
      if [ -z "$refresh_id" ]; then
        echo "WARNING: Refresh command failed. Skipping this episode."
        sleep 10
        continue
      fi
      echo "Refresh command accepted (ID: $refresh_id). Waiting 5s..."
      sleep 5

      echo " - Searching for quality upgrade..."
      local search_cmd
      search_cmd=$(episode_search_episodes "[$episode_id]")
      local search_id
      search_id=$(echo "$search_cmd" | jq '.id // empty')
      if [ -n "$search_id" ]; then
        echo "Search command accepted (ID: $search_id)."
        echo "$episode_id" >> "$PROCESSED_UPGRADE_FILE"
        processed_episode_ids+=("$episode_id")
        episodes_processed=$((episodes_processed + 1))
        echo "Processed $episodes_processed/$MAX_UPGRADES upgrade episodes this cycle."
      else
        echo "WARNING: Search command failed for episode ID $episode_id."
        sleep 10
      fi
    done

    if [ "$MAX_UPGRADES" -gt 0 ] && [ "$episodes_processed" -ge "$MAX_UPGRADES" ]; then
      echo "Reached MAX_UPGRADES=$MAX_UPGRADES for this cycle."
      break
    fi

    if [ "$RANDOM_SELECTION" = "false" ]; then
      page=$((page + 1))
      [ "$page" -gt "$total_pages" ] && break
    else
      echo "Completed processing page $page in random mode. Continuing..."
    fi
  done

  echo "Completed processing $episodes_processed upgrade episodes for this cycle."
  local processed_count
  processed_count=$(wc -l < "$PROCESSED_UPGRADE_FILE")
  if [ "$processed_count" -gt 1000 ]; then
    echo "Processed upgrade episodes list is getting large. Truncating to last 500 entries."
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
      process_missing_episodes
      ;;
    upgrade)
      process_cutoff_upgrades
      ;;
    both)
      process_missing_episodes
      process_cutoff_upgrades
      ;;
    *)
      echo "Unknown SEARCH_TYPE=$SEARCH_TYPE. Use 'missing','upgrade','both'."
      ;;
  esac

  # Calculate minutes remaining until the state files are reset
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
  sleep "$SLEEP_DURATION"
done
