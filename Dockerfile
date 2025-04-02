# Use a lightweight Alpine Linux base image
FROM alpine:latest

# Install bash, curl, and jq (required by the script)
RUN apk add --no-cache bash curl jq

# Set default environment variables for Sonarr Hunter
ENV API_KEY="your-api-key" \
    API_URL="http://your-sonarr-address:8989" \
    MAX_SHOWS="1" \
    SLEEP_DURATION="900" \
    RANDOM_SELECTION="true" \
    MONITORED_ONLY="false"

# Copy your sonarr-hunter.sh script into the container
COPY sonarr-hunter.sh /usr/local/bin/sonarr-hunter.sh

# Make the script executable
RUN chmod +x /usr/local/bin/sonarr-hunter.sh

# Set the default command to run the script
ENTRYPOINT ["/usr/local/bin/sonarr-hunter.sh"]
