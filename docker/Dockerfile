# Use a lightweight Alpine Linux base image
FROM alpine:latest

# Install bash, curl, and jq (required by the script)
RUN apk add --no-cache bash curl jq

# Set default environment variables for Sonarr configuration
ENV SONARR_URL="http://localhost:8989" \
    SONARR_API_KEY="your_default_api_key" \
    MAX_SHOWS="1" \
    SLEEP_DURATION="900" \
    RANDOM_SELECTION="true"

# Copy the sonarr-hunter.sh script into the container
COPY sonarr-hunter.sh /usr/local/bin/sonarr-hunter.sh

# Make the script executable
RUN chmod +x /usr/local/bin/sonarr-hunter.sh

# Set the default command to run the script
ENTRYPOINT ["/usr/local/bin/sonarr-hunter.sh"]
