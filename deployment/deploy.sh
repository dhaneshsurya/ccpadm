#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

PROJECT_DIR="/home/ubuntu/django_ccp"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

echo "=========================================="
echo " Starting Django CCP Deployment Update... "
echo "=========================================="

cd "$PROJECT_DIR"

# Pull latest changes (make sure you have set up git credentials or ssh keys on EC2)
echo "1. Pulling latest code from git..."
git pull

# Ensure project virtual environment exists (Debian/Ubuntu blocks system-wide pip)
echo "2. Preparing virtual environment..."
if [ ! -x "$PYTHON_BIN" ]; then
    echo "   Creating venv at $VENV_DIR ..."
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERROR: python3 is not installed. Run: sudo apt update && sudo apt install -y python3 python3-venv python3-full"
        exit 1
    fi
    python3 -m venv "$VENV_DIR"
fi

# Install/update packages inside the venv (never use system pip on EC2)
echo "3. Installing dependencies..."
"$PIP_BIN" install --upgrade pip
"$PIP_BIN" install -r requirements.txt

# Apply database migrations
echo "4. Running database migrations..."
"$PYTHON_BIN" manage.py migrate --noinput

# Collect static files
echo "5. Collecting static files..."
"$PYTHON_BIN" manage.py collectstatic --noinput

# Restart systemd services to pick up changes
echo "6. Restarting Gunicorn..."
sudo systemctl restart gunicorn

echo "7. Restarting Nginx..."
sudo systemctl restart nginx

echo "=========================================="
echo "          Deployment Successful!          "
echo "=========================================="