FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHROME_SANDBOX=false \
    HEARTBEAT_FILE=/tmp/heartbeat

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates chromium xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 bot

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY src ./src
RUN chmod 755 /usr/local/bin/entrypoint.sh && mkdir logs && chown bot:bot logs

USER bot

# The bot touches the file every 30 seconds while its event loop is running.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD test -n "$(find "$HEARTBEAT_FILE" -newermt '-90 seconds' 2>/dev/null)"

ENTRYPOINT ["entrypoint.sh"]
CMD ["python", "src/main.py"]
