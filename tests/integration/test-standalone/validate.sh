#!/bin/bash
result=$(jericho --get-records)
echo $result
lines=$(echo $result |grep -o http:// |wc -l)
echo $lines
if [[ $lines == 50 ]]; then
    exit 0
else
    exit 1
fi