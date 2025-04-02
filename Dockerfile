# Use a lightweight Alpine Linux base image
FROM alpine:latest

# Install bash, curl, and jq
RUN apk add --no-cache bash curl jq

# Set default environment variables
ENV API_KEY="your-api-key" \
    API_URL="http://your-sonarr-address:8989" \
    SEARCH_TYPE="missing" \
    MAX_SHOWS="1" \
    SLEEP_DURATION="900" \
    RANDOM_SELECTION="true" \
    MONITORED_ONLY="true"

# Copy the script
COPY sonarr-hunter.sh /usr/local/bin/sonarr-hunter.sh
RUN chmod +x /usr/local/bin/sonarr-hunter.sh

# Default command
ENTRYPOINT ["/usr/local/bin/sonarr-hunter.sh"]
