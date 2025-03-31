#!/usr/bin/env bash
# ---------------------------
# Configuration
# ---------------------------
API_KEY="a03c86b6292c4bd48cd5e3b84e5a4702"
SONARR_URL="http://10.0.0.10:8989"
# How many shows to process before restarting the search cycle
MAX_SHOWS=1
# Sleep duration in seconds after finding a show with missing episodes (900=15min, 600=10min)
SLEEP_DURATION=900
# Set to true to pick shows randomly, false to go in order
RANDOM_SELECTION=true

# ---------------------------
# Main infinite loop
# ---------------------------
while true; do
  # ---------------------------
  # Fetch only shows with missing episodes from Sonarr
  # ---------------------------
  echo "Retrieving missing episodes data from Sonarr..."
  # Get all shows first
  SHOWS_JSON=$(curl -s \
    -H "X-Api-Key: $API_KEY" \
    "$SONARR_URL/api/v3/series")

  # If the above command fails or returns nothing, wait and retry
  if [ -z "$SHOWS_JSON" ]; then
    echo "ERROR: Unable to retrieve series data from Sonarr. Retrying in 60 seconds..."
    sleep 60
    continue
  fi

  # Filter to only get shows with missing episodes
  INCOMPLETE_SHOWS_JSON=$(echo "$SHOWS_JSON" | jq '[.[] | select(has("statistics") and .statistics.episodeCount > .statistics.episodeFileCount)]')
  
  # Count how many incomplete shows are in the list
  TOTAL_INCOMPLETE=$(echo "$INCOMPLETE_SHOWS_JSON" | jq 'length')
  if [ "$TOTAL_INCOMPLETE" -eq 0 ]; then
    echo "No shows with missing episodes found in Sonarr. Waiting 60 seconds before checking again..."
    sleep 60
    continue
  fi
  echo "Found $TOTAL_INCOMPLETE show(s) with missing episodes."

  # ---------------------------
  # Process incomplete shows based on configuration
  # ---------------------------
  echo "Using ${RANDOM_SELECTION:+random}${RANDOM_SELECTION:-sequential} selection."
  echo "Will process up to ${MAX_SHOWS:-all} shows with ${SLEEP_DURATION}s pause between each."

  SHOWS_PROCESSED=0
  ALREADY_CHECKED=()

  while true; do
    # Check if we've reached the maximum number of shows to process
    if [ "$MAX_SHOWS" -gt 0 ] && [ "$SHOWS_PROCESSED" -ge "$MAX_SHOWS" ]; then
      echo "Reached maximum number of shows to process ($MAX_SHOWS). Restarting search cycle..."
      break
    fi

    # Check if we've checked all incomplete shows
    if [ ${#ALREADY_CHECKED[@]} -eq "$TOTAL_INCOMPLETE" ] || [ "$TOTAL_INCOMPLETE" -eq 0 ]; then
      echo "All shows with missing episodes have been checked. Waiting before starting a new cycle..."
      sleep 60
      break
    fi

    # Select next show index based on selection method
    if [ "$RANDOM_SELECTION" = true ] && [ "$TOTAL_INCOMPLETE" -gt 1 ]; then
      # Keep generating random indices until we find one we haven't checked yet
      while true; do
        INDEX=$((RANDOM % TOTAL_INCOMPLETE))
        # Check if this index has already been processed
        if [[ ! " ${ALREADY_CHECKED[*]} " =~ " ${INDEX} " ]]; then
          break
        fi
      done
    else
      # Find the first index that hasn't been checked yet
      for ((i=0; i<TOTAL_INCOMPLETE; i++)); do
        if [[ ! " ${ALREADY_CHECKED[*]} " =~ " ${i} " ]]; then
          INDEX=$i
          break
        fi
      done
    fi

    # Add this index to the list of checked indices
    ALREADY_CHECKED+=("$INDEX")

    # Extract show information
    SHOW=$(echo "$INCOMPLETE_SHOWS_JSON" | jq ".[$INDEX]")
    SHOW_ID=$(echo "$SHOW" | jq '.id')
    SHOW_TITLE=$(echo "$SHOW" | jq -r '.title')
    EPISODE_COUNT=$(echo "$SHOW" | jq '.statistics.episodeCount')
    EPISODE_FILE_COUNT=$(echo "$SHOW" | jq '.statistics.episodeFileCount')
    MISSING=$((EPISODE_COUNT - EPISODE_FILE_COUNT))
    
    echo "Selected show \"$SHOW_TITLE\" with $MISSING missing episode(s)..."
    
    # ---------------------------
    # Step 1: Refresh the series to make sure Sonarr has latest information
    # ---------------------------
    echo "1. Refreshing series information for \"$SHOW_TITLE\" (ID: $SHOW_ID)..."
    
    REFRESH_COMMAND=$(curl -s -X POST \
      -H "X-Api-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"RefreshSeries\",\"seriesId\":$SHOW_ID}" \
      "$SONARR_URL/api/v3/command")
    
    # Check if the refresh command succeeded
    REFRESH_ID=$(echo "$REFRESH_COMMAND" | jq '.id // empty')
    if [ -n "$REFRESH_ID" ]; then
      echo "Refresh command accepted (ID: $REFRESH_ID)."
      
      # Wait for the refresh to complete
      echo "Waiting for refresh to complete..."
      sleep 5
      
      # ---------------------------
      # Step 2: Tell Sonarr to search for missing episodes
      # ---------------------------
      echo "2. Telling Sonarr to perform a missing-episode search for \"$SHOW_TITLE\" (ID: $SHOW_ID)..."
      
      SEARCH_COMMAND=$(curl -s -X POST \
        -H "X-Api-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"MissingEpisodeSearch\",\"seriesId\":$SHOW_ID}" \
        "$SONARR_URL/api/v3/command")
      
      # Verify the response from Sonarr
      SEARCH_ID=$(echo "$SEARCH_COMMAND" | jq '.id // empty')
      if [ -n "$SEARCH_ID" ]; then
        echo "Search command accepted (ID: $SEARCH_ID)."
        
        # Wait a moment to let Sonarr process the command
        echo "Waiting 2 seconds to check command status..."
        sleep 2
        
        # Check the status of the command
        COMMAND_STATUS=$(curl -s \
          -H "X-Api-Key: $API_KEY" \
          "$SONARR_URL/api/v3/command/$SEARCH_ID" | jq -r '.status')
        
        echo "Command status: $COMMAND_STATUS"
        SHOWS_PROCESSED=$((SHOWS_PROCESSED + 1))
        
        # Sleep after processing a show with missing episodes
        echo "Show with missing episodes processed. Sleeping for $SLEEP_DURATION seconds to avoid overloading indexers..."
        sleep "$SLEEP_DURATION"
      else
        echo "WARNING: Search command did not return an ID. Response was:"
        echo "$SEARCH_COMMAND"
        echo "Trying alternative commands..."
        
        # Try an alternative command for Sonarr v3
        SEARCH_COMMAND2=$(curl -s -X POST \
          -H "X-Api-Key: $API_KEY" \
          -H "Content-Type: application/json" \
          -d "{\"name\":\"EpisodeSearch\",\"seriesId\":$SHOW_ID}" \
          "$SONARR_URL/api/v3/command")
        
        SEARCH_ID2=$(echo "$SEARCH_COMMAND2" | jq '.id // empty')
        if [ -n "$SEARCH_ID2" ]; then
          echo "Alternative search command accepted (ID: $SEARCH_ID2)."
          SHOWS_PROCESSED=$((SHOWS_PROCESSED + 1))
          echo "Show with missing episodes processed. Sleeping for $SLEEP_DURATION seconds to avoid overloading indexers..."
          sleep "$SLEEP_DURATION"
        else
          echo "All search commands failed. Skipping this show."
          sleep 10
        fi
      fi
    else
      echo "WARNING: Refresh command did not return an ID. Response was:"
      echo "$REFRESH_COMMAND"
      echo "Skipping search for this show."
      
      # Sleep a shorter time since we didn't actually do a search
      sleep 10
    fi
  done

  echo "Done. Processed $SHOWS_PROCESSED shows with missing episodes in this cycle."
  
  # If we didn't find any shows to process in this cycle, wait a bit before starting a new cycle
  if [ "$SHOWS_PROCESSED" -eq 0 ]; then
    echo "No shows with missing episodes processed this cycle. Waiting 60 seconds before starting a new cycle..."
    sleep 60
  fi
done
