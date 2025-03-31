# Use a lightweight Alpine Linux base image
FROM alpine:latest

# Install necessary packages: bash, curl, jq
RUN apk add --no-cache bash curl jq

# Set default environment variables
# These can be overridden at runtime
ENV API_KEY="your-api-key" \
    API_URL="http://your-address:8989" \
    MAX_SHOWS="1" \
    SLEEP_DURATION="900" \
    RANDOM_SELECTION="true"

# Copy your sonarr-hunter.sh script into the container
COPY sonarr-hunter.sh /usr/local/bin/sonarr-hunter.sh

# Make the script executable
RUN chmod +x /usr/local/bin/sonarr-hunter.sh

# Set the default command to run the script
ENTRYPOINT ["/usr/local/bin/sonarr-hunter.sh"]
