#!/bin/bash

echo "🚀 Starting Fanvy Local Server..."
echo ""

# Activate virtual environment if it exists
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  No virtual environment found. Run: python3 -m venv .venv"
fi

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "🌐 Fanvy will be available at: http://localhost:5000"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Run the app
python app.py
