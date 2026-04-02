#!/bin/bash

# LinkedIn MCP Pro Max - Automated Setup Script
# Description: Streamlines the initialization of the LinkedIn MCP Pro Max project.

set -e

# Change to the project root directory (one level up from the scripts/ folder)
cd "$(dirname "$0")/.."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}🌐 LinkedIn MCP Pro Max - Setup Wizard${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. Check for uv
if ! command -v uv &> /dev/null
then
    echo -e "${RED}Error: 'uv' is not installed.${NC}"
    echo -e "${YELLOW}Please install uv first: https://github.com/astral-sh/uv${NC}"
    exit 1
fi

echo -e "${GREEN}[1/4] Syncing dependencies with uv...${NC}"
uv sync

# 2. Bootstrap .env
if [ ! -f .env ]; then
    echo -e "${GREEN}[2/4] Bootstrapping .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Action Required: Please update .env with your credentials!${NC}"
else
    echo -e "${GREEN}[2/4] .env file already exists. Skipping bootstrap.${NC}"
fi

# 3. Provision Stealth Browser Engine
echo -e "${GREEN}[3/4] Provisioning Stealth Browser (Patchright/Chromium)...${NC}"
uv run python -m patchright install chromium

# 4. Finalizing
echo -e "${GREEN}[4/4] Finalizing setup...${NC}"

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}✅ Setup Complete! LinkedIn MCP Pro Max is ready.${NC}"
echo -e "${GREEN}====================================================${NC}"

echo -e "\n${BLUE}Next Steps:${NC}"
echo -e "1. Edit the ${YELLOW}.env${NC} file and add your LinkedIn credentials."
echo -e "2. Run ${YELLOW}uv run linkedin-mcp-pro-max --status${NC} to verify."
echo -e "3. Start using the server in your AI workflows!"

echo -e "\n${BLUE}For help, run:${NC}"
echo -e "uv run linkedin-mcp-pro-max --help\n"
