#!/bin/bash

export ORACLE_HOME=%ORACLE_HOME%
export ORACLE_SID=%ORACLE_SID%
export PATH=$ORACLE_HOME/bin:$ORACLE_HOME/OPatch:$PATH
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH

pmonpid=$(ps -ef | grep ora_pmon_$ORACLE_SID | grep -v grep | sed -nr "s/^([^ ]+)([ ]+)([0-9]+)(.*)ora_pmon_($ORACLE_SID)$/\3/p")

if [ -z "${pmonpid}" ]; then
   echo "STOPPED"
   exit 0
fi

if test -r /proc/${pmonpid}/exe; then
   lsout=`ls -l /proc/${pmonpid}/exe`
else
   lsout=`sudo -n ls -l /proc/${pmonpid}/exe 2> /dev/null`
fi

ora_home=`echo "$lsout" | awk -F'>' '{ print $2 }' | sed 's/ //' | sed 's/\/bin\/oracle$//'`

if [ ! -z "${ora_home}" ] && [ "$ORACLE_HOME" != "$ora_home" ]; then
   echo "STOPPED"
   exit 1
fi

sqlout=`sqlplus -s / as sysdba <<EOF
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
SELECT VALUE FROM V\\$DIAG_INFO WHERE NAME = 'ORACLE_HOME';
SELECT STATUS FROM V\\$INSTANCE;
EOF`

sqlcode=$?

if   [ $sqlcode != 0 ] && [[ "$sqlout" == *"ORA-01012: not logged on"* ]] && [[ "$sqlout" == *"Process ID: 0"* ]]; then
   sleep 10s
   pmonpid=$(ps -ef | grep ora_pmon_$ORACLE_SID | grep -v grep | sed -nr "s/^([^ ]+)([ ]+)([0-9]+)(.*)ora_pmon_($ORACLE_SID)$/\3/p")
   if [ -z "${pmonpid}" ]; then
      echo "STOPPED"
      exit 0
   else
      echo "ORA-01090: shutdown in progress - connection is not permitted"
      exit 1
   fi
elif [ $sqlcode == 0 ]; then
   ora_home=`echo "$sqlout" | awk 'NR==1{print $1}'`
   instancestatus=`echo "$sqlout" | awk 'NR==2{print $1}'`
   if   [ ! -z "${ora_home}" ] && [ "$ORACLE_HOME" != "$ora_home" ]; then
      echo "STOPPED"
      exit 1
   elif [ ! -z "${instancestatus}" ] && [ "$ORACLE_HOME" = "$ora_home" ]; then
      echo "${instancestatus}"
      if [ "${instancestatus}" = "OPEN" ]; then
         active=`sqlplus -s / as sysdba <<EOF
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
         SELECT to_char(SUM(CASE S.STATUS WHEN 'ACTIVE' THEN 1 ELSE 0 END)) ACTIVE
         FROM GV\\$SESSION S
         WHERE S.TYPE != 'BACKGROUND'
         GROUP BY S.INST_ID;`
         echo "ACTIVE_USERS: $active"
      fi
      exit 0
   else
      exit 1
   fi
else
   echo "$sqlout"
   exit 1
fi