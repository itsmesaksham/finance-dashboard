#!/bin/bash

# Finance Dashboard Setup Script
# This script sets up the development environment

set -e  # Exit on any error

echo "🔧 Setting up Finance Dashboard development environment..."

# Check Python version
python3 --version || {
    echo "❌ Python 3 is required but not found. Please install Python 3.8 or higher."
    exit 1
}

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists."
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Create data directory if it doesn't exist
mkdir -p data

# Initialize database
echo "🗄️ Initializing database..."
python -c "
import sys
sys.path.insert(0, 'src')
from database.db import init_db
init_db()
print('✅ Database initialized successfully!')
"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the application:"
echo "  ./scripts/start.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python -m streamlit run app.py"
echo ""
