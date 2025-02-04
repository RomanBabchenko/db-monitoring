#!/bin/bash
FREE_DATA=`free -m | grep Mem`
CURRENT=`echo $FREE_DATA | cut -f3 -d' '`
TOTAL=`echo $FREE_DATA | cut -f2 -d' '`
echo CPU: `top -b -n1 | grep "Cpu(s)" | awk '{print $2 + $4}'` RAM: $(echo "scale = 2; $CURRENT/$TOTAL*100" | bc) HDD: `df -lh | awk '{if ($6 == "/") { print $5 }}' | head -1 | cut -d'%' -f1`
