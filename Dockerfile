FROM python:3.15-slim

# Logs go straight to the container log instead of being block-buffered.
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY miss_islington miss_islington

# cabotage runs the release image as `nobody`. The worker clones cpython into
# the working directory and runs `git config --global`, so both the working
# directory and HOME must be writable by that user.
ENV HOME=/app
RUN chown -R nobody:nogroup /app

CMD ["python", "-m", "miss_islington"]
