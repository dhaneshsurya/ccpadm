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
echo "NOTE: Do NOT run bare 'pip install' on EC2."
echo "      This script installs packages inside: $VENV_DIR"
echo ""

cd "$PROJECT_DIR"

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "WARNING: $PROJECT_DIR/.env is missing."
    echo "         OTP / registration emails will fail until you create .env from .env.example"
    echo "         and set EMAIL_HOST_USER + EMAIL_HOST_PASSWORD (Gmail App Password)."
fi

ensure_python_prereqs() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERROR: python3 is not installed."
        echo "Run: sudo apt update && sudo apt install -y python3 python3-venv python3-full"
        exit 1
    fi
    if ! python3 -c "import venv" 2>/dev/null; then
        echo "ERROR: python3-venv is not installed (required on Ubuntu/Debian)."
        echo "Run: sudo apt update && sudo apt install -y python3-venv python3-full"
        exit 1
    fi
}

ensure_venv() {
    ensure_python_prereqs

    if [ ! -x "$PYTHON_BIN" ] || [ ! -x "$PIP_BIN" ]; then
        echo "   Creating virtual environment at $VENV_DIR ..."
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
    fi

    if [ ! -x "$PIP_BIN" ]; then
        echo "ERROR: venv pip not found at $PIP_BIN"
        exit 1
    fi

    # Guard against accidentally using system pip (PEP 668 externally-managed-environment).
    PIP_REALPATH="$(readlink -f "$PIP_BIN" 2>/dev/null || echo "$PIP_BIN")"
    if [[ "$PIP_REALPATH" != *"$VENV_DIR"* ]]; then
        echo "ERROR: pip is not inside the project venv."
        echo "       Expected venv pip, got: $PIP_REALPATH"
        exit 1
    fi
}

# Pull latest changes (make sure you have set up git credentials or ssh keys on EC2)
echo "1. Pulling latest code from git..."
git pull

# Ensure project virtual environment exists (Debian/Ubuntu blocks system-wide pip)
echo "2. Preparing virtual environment..."
ensure_venv

# Install/update packages inside the venv (never use system pip on EC2)
echo "3. Installing dependencies into venv..."
"$PIP_BIN" install --upgrade pip
"$PIP_BIN" install -r requirements.txt

# Apply database migrations
echo "4. Running database migrations..."
"$PYTHON_BIN" manage.py migrate --noinput

# Collect static files
echo "5. Collecting static files..."
"$PYTHON_BIN" manage.py collectstatic --noinput

echo "5b. Checking email configuration..."
"$PYTHON_BIN" manage.py check_email_config || true

echo "6. Updating Gunicorn service..."
sudo cp "$PROJECT_DIR/deployment/gunicorn.service" /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload

# Restart systemd services to pick up changes
echo "7. Restarting Gunicorn..."
sudo systemctl restart gunicorn

echo "8. Restarting Nginx..."
sudo systemctl restart nginx

echo "=========================================="
echo "          Deployment Successful!          "
echo "=========================================="