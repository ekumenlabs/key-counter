#! /bin/bash

set -e

IDS=$(xinput list | egrep -i "keyboard.*id" | grep -vi virtual | cut -d= -f 2 | cut -f 1)

echo "You keyboard ID is probably on of these numbers: ${IDS}"
echo ""
echo "(Try running 'xinput list' to get descriptions... it might help)"
