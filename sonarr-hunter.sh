#!/usr/bin/env bash
# ---------------------------
# Configuration
# ---------------------------
API_KEY="a03c86b6292c4bd48cd5e3b84e5a4702"
SONARR_URL="http://10.0.0.10:8989"
# How many shows to process before restarting the search cycle
MAX_SHOWS=1
# Sleep duration in seconds after finding a show with missing episodes
SLEEP_DURATION=30
# Set to true to pick shows randomly, false to go in order
RANDOM_SELECTION=true

# ---------------------------
# Main infinite loop
# ---------------------------
while true; do
  # ---------------------------
  # Fetch all shows from Sonarr
  # ---------------------------
  echo "Retrieving all series from Sonarr..."
  SHOWS_JSON=$(curl -s \
    -H "X-Api-Key: $API_KEY" \
    "$SONARR_URL/api/v3/series")

  # If the above command fails or returns nothing, wait and retry
  if [ -z "$SHOWS_JSON" ]; then
    echo "ERROR: Unable to retrieve series data from Sonarr. Retrying in 60 seconds..."
    sleep 60
    continue
  fi

  # Count how many shows are in the list
  TOTAL_SHOWS=$(echo "$SHOWS_JSON" | jq 'length')
  if [ "$TOTAL_SHOWS" -eq 0 ]; then
    echo "No shows found in Sonarr. Waiting 60 seconds before checking again..."
    sleep 60
    continue
  fi
  echo "Found $TOTAL_SHOWS show(s)."

  # ---------------------------
  # Process shows based on configuration
  # ---------------------------
  echo "Looking for incomplete shows..."
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

    # Check if we've checked all shows
    if [ ${#ALREADY_CHECKED[@]} -eq "$TOTAL_SHOWS" ]; then
      echo "All shows have been checked. No more incomplete shows found. Waiting before starting a new cycle..."
      sleep "$SLEEP_DURATION"
      break
    fi

    # Select next show index based on selection method
    if [ "$RANDOM_SELECTION" = true ]; then
      # Keep generating random indices until we find one we haven't checked yet
      while true; do
        INDEX=$((RANDOM % TOTAL_SHOWS))
        # Check if this index has already been processed
        if [[ ! " ${ALREADY_CHECKED[*]} " =~ " ${INDEX} " ]]; then
          break
        fi
      done
    else
      # Find the first index that hasn't been checked yet
      for ((i=0; i<TOTAL_SHOWS; i++)); do
        if [[ ! " ${ALREADY_CHECKED[*]} " =~ " ${i} " ]]; then
          INDEX=$i
          break
        fi
      done
    fi

    # Add this index to the list of checked indices
    ALREADY_CHECKED+=("$INDEX")

    # Extract show information
    SHOW=$(echo "$SHOWS_JSON" | jq ".[$INDEX]")
    SHOW_ID=$(echo "$SHOW" | jq '.id')
    SHOW_TITLE=$(echo "$SHOW" | jq -r '.title')
    
    # Check if show has statistics (some might not)
    HAS_STATS=$(echo "$SHOW" | jq 'has("statistics")')
    
    if [ "$HAS_STATS" = "true" ]; then
      EPISODE_COUNT=$(echo "$SHOW" | jq '.statistics.episodeCount')
      EPISODE_FILE_COUNT=$(echo "$SHOW" | jq '.statistics.episodeFileCount')
      
      echo "Checking \"$SHOW_TITLE\"..."
      
      if [ "$EPISODE_FILE_COUNT" -lt "$EPISODE_COUNT" ]; then
        # Incomplete Show
        MISSING=$((EPISODE_COUNT - EPISODE_FILE_COUNT))
        echo "===> \"$SHOW_TITLE\" is incomplete!"
        echo "     Missing $MISSING episode(s): $EPISODE_FILE_COUNT/$EPISODE_COUNT collected."
        
        # ---------------------------
        # Tell Sonarr to download any missing episodes for this show
        # ---------------------------
        echo "Telling Sonarr to perform a missing-episode search for \"$SHOW_TITLE\" (ID: $SHOW_ID)..."
        
        COMMAND_PAYLOAD=$(cat <<EOF
{
  "name": "MissingEpisodeSearch",
  "seriesId": $SHOW_ID
}
EOF
        )
        
        COMMAND_RESPONSE=$(curl -s -X POST \
          -H "X-Api-Key: $API_KEY" \
          -H "Content-Type: application/json" \
          -d "$COMMAND_PAYLOAD" \
          "$SONARR_URL/api/v3/command")
        
        # Verify the response from Sonarr
        COMMAND_ID=$(echo "$COMMAND_RESPONSE" | jq '.id // empty')
        if [ -n "$COMMAND_ID" ]; then
          echo "Sonarr accepted command (ID: $COMMAND_ID)."
          
          # Wait a moment to let Sonarr process the command
          echo "Waiting 2 seconds to check command status..."
          sleep 2
          
          # Check the status of the command
          COMMAND_STATUS=$(curl -s \
            -H "X-Api-Key: $API_KEY" \
            "$SONARR_URL/api/v3/command/$COMMAND_ID" | jq -r '.status')
          
          echo "Command status: $COMMAND_STATUS"
          SHOWS_PROCESSED=$((SHOWS_PROCESSED + 1))
          
          # Sleep after finding and processing a show with missing episodes
          echo "Show with missing episodes found. Sleeping for $SLEEP_DURATION seconds to avoid overloading indexers..."
          sleep "$SLEEP_DURATION"
        else
          echo "WARNING: Sonarr command did not return an ID. Response was:"
          echo "$COMMAND_RESPONSE"
        fi
      else
        # Show is fully downloaded
        echo "===> \"$SHOW_TITLE\" is complete. Looking for another (no sleep needed)..."
      fi
    else
      echo "===> \"$SHOW_TITLE\" lacks statistics. Skipping."
    fi
  done

  echo "Done. Processed $SHOWS_PROCESSED incomplete shows in this cycle."
  
  # If we didn't find any shows to process in this cycle, wait a bit before starting a new cycle
  if [ "$SHOWS_PROCESSED" -eq 0 ]; then
    echo "No incomplete shows processed this cycle. Waiting 60 seconds before starting a new cycle..."
    sleep 60
  fi
done
