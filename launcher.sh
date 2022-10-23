#!/bin/sh
# launcher.sh

export GOOGLE_APPLICATION_CREDENTIALS=/home/pi/cloud_speech.json
LIST=$(ps -ef | grep speach_main | wc -l)
if [ "$LIST" -le 1 ]; then
   python3 /home/pi/AIY-projects-python/src/examples/voice/speach_main.py
fi
