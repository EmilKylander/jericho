jericho --max-requests 10 --input tests/integration/test-cluster/host.txt --log-level debug --resolve-list /resolve.txt --use-servers
echo "Verifying output.."

result=$(jericho --get-records)
echo $result
lines=$(echo $result |grep -o http:// |wc -l)
echo $lines
if [[ $lines == 50 ]]; then
    exit 0
else
    exit 1
fi