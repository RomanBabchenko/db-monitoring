#!/bin/bash

export ORACLE_HOME=%ORACLE_HOME%
export ORACLE_SID=%INSTANCE_NAME%
export PATH=$ORACLE_HOME/bin:$ORACLE_HOME/OPatch:$PATH
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH
export INSTANCE_TYPE=ASM

asm_pid=$(ps -ef|grep asm_pmon_$ORACLE_SID | grep -v grep | awk '{print $2}')
if [ ! -z "${asm_pid}" ];  then
   if test -r /proc/${asm_pid}/exe; then
      lsout=`ls -l /proc/${asm_pid}/exe`
   else
      lsout=`sudo -n ls -l /proc/${asm_pid}/exe 2> /dev/null`
   fi
   ora_home=$(echo "$lsout" | awk -F'>' '{ print $2 }' | sed 's/ //' | sed 's/\/bin\/oracle$//')
   if [ ! -z "${ora_home}" ] && [ "${ora_home}" == "$ORACLE_HOME" ] && test -d "$ora_home"; then
      echo "STARTED"
   else
      asmstatus=`sqlplus -s / as sysasm <<EOF
whenever sqlerror exit failure
whenever oserror exit failure
SET arraysize 1000
SET echo OFF
SET verify OFF
SET termout OFF
SET linesize 32767
SET long 90000
SET longchunksize 90000
SET trims ON
SET newpage NONE
SET pagesize 0
SET heading OFF
SET feed OFF
SET wrap ON
SET recsep OFF
SET serveroutput ON SIZE 1000000
SET autoprint OFF
SELECT STATUS FROM V\\$INSTANCE;
EOF`
        if [ $? == 0 ]; then
           echo "$asmstatus"
        else
           exit 1
        fi
   fi
else
   echo "STOPPED"
fi