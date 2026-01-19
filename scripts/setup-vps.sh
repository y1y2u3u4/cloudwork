#!/bin/bash
# =====================================
# CloudWork VPS Setup Script
# =====================================
# One-click installation for Ubuntu 20.04+
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/xxx/cloudwork/main/scripts/setup-vps.sh | bash
#
# Or download and run manually:
#   wget https://raw.githubusercontent.com/xxx/cloudwork/main/scripts/setup-vps.sh
#   chmod +x setup-vps.sh
#   ./setup-vps.sh

set -e

# =====================================
# Configuration
# =====================================
INSTALL_DIR="/home/claude/cloudwork"
SERVICE_NAME="cloudwork"
PYTHON_VERSION="3.11"
NODE_VERSION="20"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =====================================
# Helper Functions
# =====================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# =====================================
# Main Installation
# =====================================

log_info "======================================"
log_info "CloudWork VPS Setup"
log_info "======================================"

# Check root
check_root

# Update system
log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
log_info "Installing dependencies..."
apt-get install -y \
    curl \
    git \
    expect \
    software-properties-common

# Install Python 3.11
log_info "Installing Python ${PYTHON_VERSION}..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev

# Set Python 3.11 as default (optional)
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

# Install pip
log_info "Installing pip..."
curl -sS https://bootstrap.pypa.io/get-pip.py | python${PYTHON_VERSION}

# Install Node.js
log_info "Installing Node.js ${NODE_VERSION}..."
curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
apt-get install -y nodejs

# Install Claude Code CLI
log_info "Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# Verify installations
log_info "Verifying installations..."
python${PYTHON_VERSION} --version
node --version
npm --version
claude --version || log_warn "Claude CLI may need authentication"

# Create claude user (if not exists)
# This is required because Claude CLI cannot run with root/sudo privileges
# when using --dangerously-skip-permissions flag
if ! id "claude" &>/dev/null; then
    log_info "Creating 'claude' user..."
    useradd -m -s /bin/bash claude
    log_info "Setting up claude user environment..."
    # Create necessary directories in claude home
    mkdir -p /home/claude/.config
    mkdir -p /home/claude/.npm
    chown -R claude:claude /home/claude
fi

# Ensure claude user owns npm global packages
log_info "Configuring npm for claude user..."
mkdir -p /home/claude/.npm-global
chown -R claude:claude /home/claude/.npm-global
su - claude -c "npm config set prefix '/home/claude/.npm-global'"

# Add npm global to claude's PATH
if ! grep -q "npm-global" /home/claude/.bashrc 2>/dev/null; then
    echo 'export PATH=/home/claude/.npm-global/bin:$PATH' >> /home/claude/.bashrc
fi

# Create installation directory
log_info "Creating installation directory..."
mkdir -p ${INSTALL_DIR}
chown -R claude:claude ${INSTALL_DIR}

# Clone or copy project
log_info "Setting up project files..."
# Option 1: Clone from git (if public)
# git clone https://github.com/xxx/cloudwork.git ${INSTALL_DIR}

# Option 2: Create basic structure
mkdir -p ${INSTALL_DIR}/{src,config,data,workspace,logs}

# Create requirements.txt
cat > ${INSTALL_DIR}/requirements.txt << 'EOF'
python-telegram-bot>=20.7
python-dotenv>=1.0.0
pydantic-settings>=2.1.0
aiofiles>=23.2.1
EOF

# Install Python dependencies
log_info "Installing Python dependencies..."
pip install -r ${INSTALL_DIR}/requirements.txt

# Create .env template
if [[ ! -f ${INSTALL_DIR}/config/.env ]]; then
    cat > ${INSTALL_DIR}/config/.env.example << 'EOF'
# CloudWork Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USERS=123456789
ANTHROPIC_API_KEY=sk-ant-xxxxx
DEFAULT_MODEL=sonnet
DEFAULT_MODE=auto
COMMAND_TIMEOUT=300
EOF
    log_warn "Please edit ${INSTALL_DIR}/config/.env with your actual tokens"
    cp ${INSTALL_DIR}/config/.env.example ${INSTALL_DIR}/config/.env
fi

# Create systemd service
# IMPORTANT: Service must run as 'claude' user, NOT root
# Claude CLI's --dangerously-skip-permissions flag does not work with root/sudo
log_info "Creating systemd service..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=CloudWork - Cloud Claude Code Workspace
After=network.target

[Service]
Type=simple
# Run as 'claude' user to avoid Claude CLI permission restrictions
User=claude
Group=claude
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/config/.env
Environment=PYTHONPATH=${INSTALL_DIR}
ExecStart=/usr/bin/python${PYTHON_VERSION} -m src.bot.main
Restart=always
RestartSec=10

# Logging
StandardOutput=append:${INSTALL_DIR}/logs/cloudwork.log
StandardError=append:${INSTALL_DIR}/logs/cloudwork.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Set ownership
chown -R claude:claude ${INSTALL_DIR}

log_info "======================================"
log_info "Installation Complete!"
log_info "======================================"
log_info ""
log_info "Next steps:"
log_info "1. Edit configuration: nano ${INSTALL_DIR}/config/.env"
log_info "2. Add your bot code to: ${INSTALL_DIR}/src/"
log_info "3. Start the service: systemctl start ${SERVICE_NAME}"
log_info "4. Enable auto-start: systemctl enable ${SERVICE_NAME}"
log_info "5. Check status: systemctl status ${SERVICE_NAME}"
log_info "6. View logs: journalctl -u ${SERVICE_NAME} -f"
log_info ""
log_info "Useful commands:"
log_info "  systemctl restart ${SERVICE_NAME}  # Restart bot"
log_info "  systemctl stop ${SERVICE_NAME}     # Stop bot"
log_info "  journalctl -u ${SERVICE_NAME} -f   # Follow logs"
