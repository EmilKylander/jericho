jericho --max-requests 10 --input tests/integration/test-cluster/host.txt --log-level debug --resolve-list /resolve.txt --use-servers --converter identifier
echo "Verifying output.."

result=$(jericho --get-converter-output)
echo $result
lines=$(echo $result |grep -o .zip |wc -l)
echo $lines
if [[ $lines == 1 ]]; then
    exit 0
else
    exit 1
fi