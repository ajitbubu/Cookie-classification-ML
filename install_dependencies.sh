#!/bin/bash
# Install all required dependencies for Three-Tier Scanning System

echo "========================================"
echo "  Installing Dependencies"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
echo ""

# Install Python packages
echo "Installing Python packages..."
pip3 install playwright playwright-stealth asyncpg apscheduler redis requests pydantic fastapi uvicorn
echo ""

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium
echo ""

echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Test scanning: python3 test_scan_simple.py"
echo "2. Apply database migration: psql -d your_db -f database/migrations/005_schedule_scan_types.sql"
echo "3. Start API: uvicorn api.main:app --reload"
echo "4. Start scheduler: python3 -m services.enhanced_scheduler"
echo ""
