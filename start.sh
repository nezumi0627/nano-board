#!/bin/bash
# Nanobot Dashboard起動スクリプト

cd "$(dirname "$0")"
source venv/bin/activate
python3 app.py
