#!/bin/bash

# Finance Dashboard Startup Script
# This script starts the Streamlit application with proper environment setup

set -e  # Exit on any error

echo "🚀 Starting Finance Dashboard..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
python -c "import streamlit, pandas, plotly" 2>/dev/null || {
    echo "❌ Dependencies not found. Installing..."
    pip install -r requirements.txt
}

# Start the application
echo "🌐 Starting Streamlit application..."
echo "📊 Dashboard will be available at: http://localhost:8501"
echo "🛑 Press Ctrl+C to stop the application"
echo ""

python -m streamlit run app.py --server.port 8501

echo "👋 Finance Dashboard stopped."
