#!/usr/bin/env bash

# ---------------------------
# Configuration
# ---------------------------
# Use environment variables if provided; otherwise, fall back to defaults.
API_KEY=${API_KEY:-"your-api-key"}
API_URL=${API_URL:-"http://your-sonarr-address:8989"}

# How many items (shows/episodes) to process before restarting the search cycle
MAX_SHOWS=${MAX_SHOWS:-1}

# Sleep duration in seconds after processing each show or upgrade (900=15min)
SLEEP_DURATION=${SLEEP_DURATION:-900}

# Set to true to pick items randomly, false to go in order
RANDOM_SELECTION=${RANDOM_SELECTION:-true}

# If MONITORED_ONLY is "true", only missing or upgrade episodes from monitored shows
MONITORED_ONLY=${MONITORED_ONLY:-false}

# SEARCH_TYPE controls what we search for:
# - "missing" => Only find shows with missing episodes
# - "upgrade" => Only find episodes that don't meet quality cutoff
# - "both"    => Do missing + upgrade checks each cycle
SEARCH_TYPE=${SEARCH_TYPE:-"missing"}

# ---------------------------
# Helper: Sonarr API calls
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
  # If you want to do a full search of the entire series for potential upgrades
  local series_id="$1"
  curl -s -X POST \
    -H "X-Api-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"EpisodeSearch\",\"seriesId\":$series_id}" \
    "$API_URL/api/v3/command"
}

episode_search_episodes() {
  # If you prefer to search for specific episodes by ID
  local episode_ids="$1" # JSON array of episode IDs, e.g. "[123,456]"
  curl -s -X POST \
    -H "X-Api-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"EpisodeSearch\",\"episodeIds\":$episode_ids}" \
    "$API_URL/api/v3/command"
}

get_cutoff_unmet() {
  # The "wanted/cutoff" endpoint returns episodes not meeting the quality cutoff
  # We'll request up to 200 per page. Adjust if needed.
  local page="${1:-1}"
  curl -s -H "X-Api-Key: $API_KEY" \
    "$API_URL/api/v3/wanted/cutoff?sortKey=airDateUtc&page=$page&pageSize=200"
}

# ---------------------------
# 1) Missing Episodes Logic
# ---------------------------
process_missing_episodes() {
  echo "=== Checking for Missing Episodes ==="
  
  local shows_json
  shows_json=$(get_series)
  if [ -z "$shows_json" ]; then
    echo "ERROR: Unable to retrieve series data from Sonarr. Retrying in 60s..."
    sleep 60
    return
  fi

  # Filter shows with missing episodes
  # If MONITORED_ONLY=true, also require "monitored == true"
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
  if [ "$total_incomplete" -eq 0 ]; then
    echo "No shows with missing episodes found. Moving on."
    return
  fi

  echo "Found $total_incomplete show(s) with missing episodes."
  local shows_processed=0
  local -a checked=()

  while true; do
    if [ "$MAX_SHOWS" -gt 0 ] && [ "$shows_processed" -ge "$MAX_SHOWS" ]; then
      echo "Reached MAX_SHOWS=$MAX_SHOWS for missing episodes search."
      break
    fi
    if [ "${#checked[@]}" -ge "$total_incomplete" ]; then
      echo "All incomplete shows processed this cycle."
      break
    fi

    # Select next show index
    local index
    if [ "$RANDOM_SELECTION" = "true" ] && [ "$total_incomplete" -gt 1 ]; then
      while true; do
        index=$((RANDOM % total_incomplete))
        if [[ ! " ${checked[*]} " =~ " $index " ]]; then
          break
        fi
      done
    else
      for ((i=0; i<total_incomplete; i++)); do
        if [[ ! " ${checked[*]} " =~ " $i " ]]; then
          index=$i
          break
        fi
      done
    fi

    checked+=("$index")
    local show
    show=$(echo "$incomplete_json" | jq ".[$index]")
    local show_id
    local show_title
    local missing
    show_id=$(echo "$show" | jq '.id')
    show_title=$(echo "$show" | jq -r '.title')
    local ep_count
    local ep_file_count
    ep_count=$(echo "$show" | jq '.statistics.episodeCount')
    ep_file_count=$(echo "$show" | jq '.statistics.episodeFileCount')
    missing=$((ep_count - ep_file_count))

    echo "Processing missing episodes for \"$show_title\" ($missing missing)."

    # Refresh Series
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

    # MissingEpisodeSearch
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

    shows_processed=$((shows_processed + 1))
    echo "Sleeping $SLEEP_DURATION seconds after missing-episode search..."
    sleep "$SLEEP_DURATION"
  done
}

# ---------------------------
# 2) Upgrade Logic (Cutoff Unmet)
# ---------------------------
process_cutoff_upgrades() {
  echo "=== Checking for Quality Upgrades (Cutoff Unmet) ==="

  # We'll pull from the "wanted/cutoff" endpoint, which lists episodes not meeting the cutoff.
  # Because results can be paginated, we can loop until no more results or we reach MAX_SHOWS.
  local page=1
  local episodes_processed=0
  local results_found=true

  while $results_found; do
    echo "Retrieving cutoff-unmet episodes (page=$page)..."
    local cutoff_json
    cutoff_json=$(get_cutoff_unmet "$page")

    # Check if we got a valid JSON response
    if ! echo "$cutoff_json" | jq empty 2>/dev/null; then
      echo "ERROR: Invalid JSON response from cutoff endpoint. Stopping upgrade search."
      results_found=false
      break
    fi

    # Check if 'records' field exists
    if ! echo "$cutoff_json" | jq 'has("records")' | grep -q "true"; then
      echo "WARNING: No 'records' field in response. Stopping upgrade search."
      results_found=false
      break
    fi

    # Check total records with proper error handling
    local records
    records=$(echo "$cutoff_json" | jq '.records')
    if [ -z "$records" ] || [ "$records" = "null" ]; then
      echo "No records field in response. Stopping upgrade search."
      results_found=false
      break
    fi

    # Make sure records is a number
    if ! [[ "$records" =~ ^[0-9]+$ ]]; then
      records=0
    fi

    if [ "$records" -eq 0 ]; then
      echo "No cutoff-unmet episodes found. Done searching for upgrades."
      results_found=false
      break
    fi

    # Check if 'episodes' field exists
    if ! echo "$cutoff_json" | jq 'has("episodes")' | grep -q "true"; then
      echo "WARNING: No 'episodes' field in response. Stopping upgrade search."
      results_found=false
      break
    fi

    # Episodes array
    local episodes
    episodes=$(echo "$cutoff_json" | jq '.episodes')
    
    # Safely check for empty array
    if [ "$episodes" = "[]" ] || [ "$episodes" = "null" ]; then
      echo "No episodes on page $page. This could be the last page."
      
      # If we're beyond page 1 and got an empty response, assume we've reached the end
      if [ "$page" -gt 1 ]; then
        echo "Reached end of results. Stopping upgrade search."
        results_found=false
        break
      else
        # Empty first page means no results at all
        echo "No upgradable episodes found."
        results_found=false
        break
      fi
    fi

    local total_eps
    total_eps=$(echo "$episodes" | jq '. | length')
    # Make sure total_eps is a number
    if ! [[ "$total_eps" =~ ^[0-9]+$ ]]; then
      total_eps=0
    fi

    echo "Found $total_eps episodes on page $page out of $records total records..."

    if [ "$total_eps" -eq 0 ]; then
      # No episodes on this page, move on
      page=$((page + 1))
      
      # Safeguard: don't go beyond a reasonable number of pages
      if [ "$page" -gt 20 ]; then
        echo "Reached 20 pages, stopping search to prevent excessive API calls."
        results_found=false
      fi
      
      continue
    fi

    # Convert episodes to an indexed array in bash
    local -a checked=()

    while true; do
      if [ "$MAX_SHOWS" -gt 0 ] && [ "$episodes_processed" -ge "$MAX_SHOWS" ]; then
        echo "Reached MAX_SHOWS=$MAX_SHOWS for upgrade searches."
        results_found=false
        break
      fi
      if [ "${#checked[@]}" -ge "$total_eps" ]; then
        echo "All episodes on this page processed."
        break
      fi

      # Pick random or next
      local index
      if [ "$RANDOM_SELECTION" = "true" ] && [ "$total_eps" -gt 1 ]; then
        while true; do
          index=$((RANDOM % total_eps))
          if [[ ! " ${checked[*]} " =~ " $index " ]]; then
            break
          fi
        done
      else
        for ((i=0; i<total_eps; i++)); do
          if [[ ! " ${checked[*]} " =~ " $i " ]]; then
            index=$i
            break
          fi
        done
      fi
      checked+=("$index")

      local episode
      episode=$(echo "$episodes" | jq ".[$index]")
      local episode_id
      episode_id=$(echo "$episode" | jq '.id')
      local show_id
      show_id=$(echo "$episode" | jq '.seriesId')
      local show_title
      show_title=$(echo "$episode" | jq -r '.seriesTitle')
      local season_num
      season_num=$(echo "$episode" | jq '.seasonNumber')
      local ep_num
      ep_num=$(echo "$episode" | jq '.episodeNumber')

      # Check monitored only for the series or episode if needed
      if [ "$MONITORED_ONLY" = "true" ]; then
        local series_monitored
        series_monitored=$(echo "$episode" | jq '.series.monitored')
        local ep_monitored
        ep_monitored=$(echo "$episode" | jq '.monitored')
        if [ "$series_monitored" != "true" ] || [ "$ep_monitored" != "true" ]; then
          echo "Skipping unmonitored episode $show_title S$season_num E$ep_num."
          continue
        fi
      fi

      echo "Upgrading $show_title (S${season_num}E${ep_num}), EpisodeID=$episode_id..."

      # 1) Refresh the series first
      echo " - Refreshing series $show_title..."
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

      # 2) EpisodeSearch for that specific episode
      echo " - Searching for better quality..."
      local episodes_ids_json="[${episode_id}]"
      local search_cmd
      search_cmd=$(episode_search_episodes "$episodes_ids_json")
      local search_id
      search_id=$(echo "$search_cmd" | jq '.id // empty')
      if [ -n "$search_id" ]; then
        echo "EpisodeSearch command accepted (ID: $search_id)."
      else
        echo "WARNING: EpisodeSearch command failed for $show_title S$season_num E$ep_num."
      fi

      episodes_processed=$((episodes_processed + 1))
      echo "Sleeping $SLEEP_DURATION seconds after upgrade search..."
      sleep "$SLEEP_DURATION"
    done

    # Done this page
    if $results_found; then
      # Only increment page if we haven't reached the end
      if [ "$((page * 200))" -lt "$records" ]; then
        page=$((page + 1))
      else
        echo "We appear to have processed all pages for cutoff-unmet."
        results_found=false
      fi
      
      # Safeguard: don't go beyond a reasonable number of pages
      if [ "$page" -gt 20 ]; then
        echo "Reached 20 pages, stopping search to prevent excessive API calls."
        results_found=false
      fi
    fi
  done
}

# ---------------------------
# Main Loop
# ---------------------------
while true; do
  # Depending on SEARCH_TYPE, do missing episodes, upgrades, or both
  case "$SEARCH_TYPE" in
    missing)
      process_missing_episodes
      ;;
    upgrade)
      process_cutoff_upgrades
      ;;
    both)
      # 1) Missing
      process_missing_episodes
      # 2) Upgrades
      process_cutoff_upgrades
      ;;
    *)
      echo "Unknown SEARCH_TYPE=$SEARCH_TYPE. Use 'missing','upgrade','both'."
      ;;
  esac

  echo "Cycle complete. Waiting 60s before next cycle..."
  sleep 60
done
