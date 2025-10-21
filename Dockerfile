# Use a lightweight Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /usr/src/app

# --- Nginx and System Dependencies ---
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and new config files
COPY app.py .
COPY nginx.conf /etc/nginx/sites-enabled/default
COPY entrypoint.sh .

# # Set permissions and make the entrypoint script executable
# RUN chmod +x entrypoint.sh

# # Nginx listens on port 80, Gunicorn listens internally on 5000
# EXPOSE 80

# # Use the entrypoint script to start both processes
# CMD ["./entrypoint.sh"]


# Expose the port Gunicorn will listen on
EXPOSE 5000

# Command to run the application with improved stability settings
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120", \
     "app:app"]