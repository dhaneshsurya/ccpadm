#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

PROJECT_DIR="/home/ubuntu/django_ccp"
VENV_DIR="$PROJECT_DIR/venv"

echo "=========================================="
echo " Starting Django CCP Deployment Update... "
echo "=========================================="

cd "$PROJECT_DIR"

# Pull latest changes (make sure you have set up git credentials or ssh keys on EC2)
echo "1. Pulling latest code from git..."
git pull

# Activate virtual environment
echo "2. Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install/update packages
echo "3. Installing dependencies..."
pip install -r requirements.txt

# Apply database migrations
echo "4. Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "5. Collecting static files..."
python manage.py collectstatic --noinput

# Restart systemd services to pick up changes
echo "6. Restarting Gunicorn..."
sudo systemctl restart gunicorn

echo "7. Restarting Nginx..."
sudo systemctl restart nginx

echo "=========================================="
echo "          Deployment Successful!          "
echo "=========================================="
