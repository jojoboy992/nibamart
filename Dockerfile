FROM python:3.12-slim

# Install Nginx and Supervisor
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /niba_mart_project

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy Nginx config
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Copy Supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make entrypoint executable
RUN chmod +x entrypoint.sh

EXPOSE 80

ENTRYPOINT ["./entrypoint.sh"]