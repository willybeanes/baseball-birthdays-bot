#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python bot.py >> logs/bot.log 2>&1
