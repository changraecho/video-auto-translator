#!/bin/bash
# Render.com build script

echo "🔧 Installing system dependencies..."
apt-get update
apt-get install -y ffmpeg

echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Build completed successfully!"