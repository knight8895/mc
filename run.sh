#!/bin/bash

# Start a new screen session in the background, run Java command
java -Xmx16G -Xms4G -jar paper.jar --nogui
 

 sleep 5

# Start another screen session in the background, run Python backup command
screen -dmS backup python backup.py

# Wait for the background processes to finish
wait
