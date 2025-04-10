FROM python:3.9-slim
WORKDIR /app

# Install dependencies
COPY primary/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory structure
RUN mkdir -p /app/primary /app/templates /app/static/css /app/static/js /config/stateful /config/settings /config/user

# Copy application files
COPY primary/ ./primary/
COPY templates/ ./templates/
COPY static/ ./static/
COPY primary/default_configs.json .

# Default environment variables (minimal set)
ENV APP_TYPE="sonarr"

# Create volume mount points
VOLUME ["/config"]

# Expose web interface port
EXPOSE 9705

# Add startup script
COPY primary/start.sh .
RUN chmod +x start.sh

# Run the startup script
CMD ["./start.sh"]