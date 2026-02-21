#!/bin/bash

# Quick Setup Script for LearnSocial iOS App
# This script helps you create the Xcode project structure

echo "🚀 LearnSocial iOS App Setup"
echo "=============================="
echo ""

# Check if Xcode is installed
if ! command -v xcodebuild &> /dev/null; then
    echo "❌ Xcode is not installed. Please install it from the Mac App Store."
    exit 1
fi

echo "✅ Xcode detected"
echo ""

# Check if Flask app is running
if curl -s http://127.0.0.1:5000 > /dev/null 2>&1; then
    echo "✅ Flask server is running on port 5000"
else
    echo "⚠️  Flask server is NOT running"
    echo "   Please start it with: python3 app.py"
    echo ""
    read -p "Do you want to start it now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Starting Flask server..."
        cd /Users/hk/learnsocial
        python3 app.py &
        FLASK_PID=$!
        echo "✅ Flask server started (PID: $FLASK_PID)"
        sleep 2
    fi
fi

echo ""
echo "📱 Next Steps:"
echo "1. Open Xcode"
echo "2. Create New Project → iOS → App"
echo "3. Name it 'LearnSocial', choose SwiftUI + Swift"
echo "4. Replace the default files with:"
echo "   - LearnSocialApp.swift"
echo "   - ContentView.swift"  
echo "   - Info.plist"
echo "5. Press ⌘+R to run in simulator"
echo ""
echo "📖 Full instructions: ios-app/README.md"
echo ""
