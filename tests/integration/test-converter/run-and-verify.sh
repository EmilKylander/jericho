jericho --max-requests 10 --input tests/integration/test-cluster/host.txt --log-level debug --resolve-list /resolve.txt --use-servers --converter identifier
echo "Verifying output.."

result=$(jericho --get-converter-output)
lines=$(echo $result |grep -o .zip |wc -l)
if [[ $lines == 1 ]]; then
    echo "Testing the resend result functionality..."
    echo "Deleting results.."
    jericho --delete-converter-result
    result=$(echo `jericho --get-converter-output`)
    echo "Converter output after deletion: $result"
    lines=$(echo $result |grep -o .zip |wc -l)

    if [[ $lines > 0 ]]; then
        echo "The converter output should be empty"
        exit 1
    fi
    workload_uuid=$(jericho --get-last-workload-uuid)
    echo "Workload UUID: $workload_uuid"
    jericho --continue-workload $workload_uuid
    result=$(jericho --get-converter-output)
    lines=$(echo $result |grep -o .zip |wc -l)
    if [[ $lines == 1 ]]; then
        exit 0
    else
        exit 1
    fi
    exit 0
else
    exit 1
fi