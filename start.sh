#!/bin/bash

echo "Starting Crawl4AI Web Crawler..."
echo "Installing dependencies (if needed)..."
pip install --break-system-packages -q -r requirements.txt

echo ""
echo "Starting server..."
python app.py
