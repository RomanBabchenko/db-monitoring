#!/bin/bash

export ORACLE_HOME=%ORACLE_HOME%
export PATH=$ORACLE_HOME/bin:$ORACLE_HOME/OPatch:$PATH
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH

lsnrname=%LISTENER_NAME%

lsnrstatus=`lsnrctl status $lsnrname`

if [ $? == 0 ]; then
   echo "Started"
else
   echo "Stopped"
fi