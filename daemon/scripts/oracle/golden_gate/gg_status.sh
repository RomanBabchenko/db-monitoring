#!/bin/bash

oraInstLoc=`cat /etc/oraInst.loc`

eval "$oraInstLoc"

inventoryfile=$inventory_loc/ContentsXML/inventory.xml

ohcount=`xmllint --xpath 'count(//HOME_LIST/HOME)' $inventoryfile`

for (( i=1; i<=$ohcount; i++ ))
do
name=`xmllint --xpath "string(//HOME_LIST/HOME[$i]//@NAME)" $inventoryfile`
path=`xmllint --xpath "string(//HOME_LIST/HOME[$i]//@LOC)" $inventoryfile`
owner=`stat -c '%U' $path/inventory/ContentsXML/comps.xml`
product=`xmllint --xpath "//COMP[1]/EXT_NAME/text()" $path/inventory/ContentsXML/comps.xml`
if [[ "$product" == "Oracle GoldenGate"* ]]; then
   depcount=`xmllint --xpath 'count(/PRD_LIST/TL_LIST/COMP/DEP_LIST/DEP)' $path/inventory/ContentsXML/comps.xml`
   for (( d=1; d<=$depcount; d++ ))
   do
      depname=`xmllint --xpath "string(/PRD_LIST/TL_LIST/COMP/DEP_LIST/DEP[$d]//@NAME)" $path/inventory/ContentsXML/comps.xml`
      if [[ "$depname" == "oracle.oggcore.ora"* ]]; then
         oraver=$(echo $depname | sed -nr 's/^oracle.oggcore.ora(.+)/\1/p')
      fi
   done
fi
done

for (( i=1; i<=$ohcount; i++ ))
do
name=`xmllint --xpath "string(//HOME_LIST/HOME[$i]//@NAME)" $inventoryfile`
path=`xmllint --xpath "string(//HOME_LIST/HOME[$i]//@LOC)" $inventoryfile`
owner=`stat -c '%U' $path/inventory/ContentsXML/comps.xml`
product=`xmllint --xpath "//COMP[1]/EXT_NAME/text()" $path/inventory/ContentsXML/comps.xml`
if [ "$product" == "Oracle Database ${oraver}" ]; then
   orahome=$path
fi
done

export ORACLE_HOME=$orahome
export PATH=$ORACLE_HOME/bin:$ORACLE_HOME/OPatch:$PATH
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$ORACLE_HOME/lib32

export OGG_HOME=%OGG_HOME%
export PATH=$OGG_HOME:$OGG_HOME/OPatch:$PATH
export LD_LIBRARY_PATH=$OGG_HOME:$LD_LIBRARY_PATH

cd $OGG_HOME

ggstatus=$(echo "INFO MANAGER" | ggsci | grep -E -i -w 'Manager is running')

if [ $? == 0 ]; then
   echo "Started"
else
   echo "Stopped"
fi