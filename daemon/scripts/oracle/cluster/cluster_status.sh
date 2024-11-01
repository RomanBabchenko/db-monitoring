#!/bin/bash

export ORACLE_HOME=%ORACLE_HOME%
export PATH=$ORACLE_HOME/bin:$ORACLE_HOME/OPatch:$PATH
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH

oracluster=%CLUSTER_NAME%

clusterconfig=`crsctl get cluster configuration 2> /dev/null`
clustername=`echo "$clusterconfig" | sed -nr 's/^Name\s+:\s(.+)/\1/p'`
clusterstatus="OFFLINE"

if [ "$oracluster" != "$clustername" ]; then
   exit 1
else
   crsctl check cluster -all | awk \
'
BEGIN { FS=":"; state = 0; i = 0; }
$1~/[\*]+/ { state = 1; }
$1!~/[\*]+/ && state == 1 { i=i+1; hosts[i]=$1; state=0; }
$1!~/[\*]+/ && state == 0 { status[i]="offline";  if ( $0 ~ /is online/ ) { status[i]="online"; } }
END {
for (j in hosts) if ( status[i] == "online" ) { $clusterstatus="ONLINE" } else { $clusterstatus="OFFLINE" }
print $clusterstatus
}
'
fi