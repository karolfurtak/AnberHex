#!/bin/bash
# AnberHex launcher dla App Center / dmenu — konwerter HEX <-> DEC
export PYSDL2_DLL_PATH="/usr/lib"
export HOME=/root
export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin"
LOG=/mnt/data/anberhex.log
echo "$(date +%H:%M:%S): start" >> "$LOG"
cd /mnt/mmc/Roms/APPS/anberhex
python3 main.py >> "$LOG" 2>&1
echo "$(date +%H:%M:%S): exit $?" >> "$LOG"
