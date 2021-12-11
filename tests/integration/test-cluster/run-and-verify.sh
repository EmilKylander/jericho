export RDMAV_FORK_SAFE=0
mpirun --allow-run-as-root --mca btl_tcp_dynamic_ports 49990-50010 -n 2 -hostfile tests/integration/test-cluster/hostfile jericho --threads 10 --input tests/integration/test-cluster/host.txt --log-level debug
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