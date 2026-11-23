#!/bin/sh
# Yad2 does not load in headless Chrome, so run it on a virtual display. The bot replaces this
# shell (exec) to receive the stop signal and shut down cleanly. xvfb-run would not pass it on.
set -eu

export DISPLAY=:99
rm -f /tmp/.X99-lock
Xvfb "$DISPLAY" -screen 0 1920x1080x24 -nolisten tcp &

exec "$@"
