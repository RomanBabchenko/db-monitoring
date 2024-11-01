#!/bin/bash

command -v systemctl >/dev/null

if [ $? != 0 ]; then
   exitcode=`sudo -ln -u $USER systemctl 1> /dev/null 2> /dev/null; echo $?`
   if [ $exitcode == 0 ]; then
      sudo systemctl list-units --type=service -all couchbase-server.service
   else
      echo "This operation requires root privileges."
      echo "Please add into /etc/sudoers the following record:"
      echo "$USER   ALL=(root)    NOPASSWD: /usr/bin/systemctl"
      exit 1
   fi
else
   systemctl list-units --type=service -all couchbase-server.service
fi