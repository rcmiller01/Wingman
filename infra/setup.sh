#!/bin/bash

# Homelab Copilot Setup Script
# Interactive configuration wizard

set -e

echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║               🏠 Homelab Copilot Setup Wizard                     ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    read -p "⚠️  .env file already exists. Overwrite? (y/N): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Copy template
cp .env.example .env

echo "📋 Let's configure your Homelab Copilot installation."
echo ""

# =============================================================================
# LLM API Keys
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 Cloud LLM Configuration (at least one recommended)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "OpenAI API Key (leave blank to skip): " OPENAI_KEY
if [ -n "$OPENAI_KEY" ]; then
    sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=$OPENAI_KEY|" .env
fi

read -p "Anthropic API Key (leave blank to skip): " ANTHROPIC_KEY
if [ -n "$ANTHROPIC_KEY" ]; then
    sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$ANTHROPIC_KEY|" .env
fi

read -p "OpenRouter API Key (leave blank to skip): " OPENROUTER_KEY
if [ -n "$OPENROUTER_KEY" ]; then
    sed -i "s|^OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=$OPENROUTER_KEY|" .env
fi

echo ""

# =============================================================================
# Ollama Configuration
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🦙 Local LLM Configuration (Ollama)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Ollama Host URL [http://host.docker.internal:11434]: " OLLAMA_HOST
OLLAMA_HOST=${OLLAMA_HOST:-http://host.docker.internal:11434}
sed -i "s|^OLLAMA_HOST=.*|OLLAMA_HOST=$OLLAMA_HOST|" .env

echo ""
echo "Available model suggestions:"
echo "  - qwen2.5:7b (recommended, good balance)"
echo "  - qwen2.5:3b (lighter, faster)"
echo "  - llama3.1:8b (alternative)"
echo ""

read -p "Ollama Model [qwen2.5:7b]: " OLLAMA_MODEL
OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:7b}
sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$OLLAMA_MODEL|" .env

echo ""

# =============================================================================
# Proxmox Configuration
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🖥️  Proxmox Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Configure Proxmox now? (y/N): " CONFIGURE_PROXMOX

if [[ "$CONFIGURE_PROXMOX" =~ ^[Yy]$ ]]; then
    read -p "Proxmox Host (e.g., https://192.168.1.100:8006): " PROXMOX_HOST
    sed -i "s|^PROXMOX_HOST=.*|PROXMOX_HOST=$PROXMOX_HOST|" .env

    read -p "Proxmox User (e.g., root@pam): " PROXMOX_USER
    sed -i "s|^PROXMOX_USER=.*|PROXMOX_USER=$PROXMOX_USER|" .env

    read -p "API Token Name: " PROXMOX_TOKEN_NAME
    sed -i "s|^PROXMOX_TOKEN_NAME=.*|PROXMOX_TOKEN_NAME=$PROXMOX_TOKEN_NAME|" .env

    read -p "API Token Value: " PROXMOX_TOKEN_VALUE
    sed -i "s|^PROXMOX_TOKEN_VALUE=.*|PROXMOX_TOKEN_VALUE=$PROXMOX_TOKEN_VALUE|" .env

    read -p "Verify SSL? (y/N): " VERIFY_SSL
    if [[ "$VERIFY_SSL" =~ ^[Yy]$ ]]; then
        sed -i "s|^PROXMOX_VERIFY_SSL=.*|PROXMOX_VERIFY_SSL=true|" .env
    else
        sed -i "s|^PROXMOX_VERIFY_SSL=.*|PROXMOX_VERIFY_SSL=false|" .env
    fi
fi

echo ""

# =============================================================================
# Summary
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Configuration Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Your .env file has been created. You can edit it manually if needed."
echo ""
echo "Next steps:"
echo "  1. Ensure Docker is running"
echo "  2. Run: docker compose up --build"
echo "  3. Access the dashboard at http://localhost:3000"
echo "  4. Backend API available at http://localhost:3001"
echo ""
echo "Happy automating! 🚀"
echo ""
