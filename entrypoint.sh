#!/bin/bash

# Start Nginx in the background
echo "Starting Nginx..."
/usr/sbin/nginx &

# Start Gunicorn in the foreground
echo "Starting Gunicorn..."
# Gunicorn now binds to localhost:5000, which is accessible by Nginx inside the container
exec gunicorn --bind 0.0.0.0:5000 app:app

# Note: The 'exec' command replaces the current shell process with Gunicorn, 
# ensuring that signals (like docker stop) are handled correctly by Gunicorn.