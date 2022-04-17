FROM ubuntu:21.10 as base
WORKDIR /app
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update --fix-missing && apt install git-all && apt-get install -y apt-transport-https
RUN apt install libopenmpi-dev python3-pip python3-dev ssh software-properties-common dnsutils -y
RUN echo 'btl_base_warn_component_unused = 0' > /etc/openmpi/openmpi-mca-params.conf 
COPY . .
RUN python3 setup.py install
RUN export RDMAV_FORK_SAFE=0
RUN jericho --import-endpoints tests/integration/test-standalone/endpoints.json
CMD cd tests/integration/test-standalone && python3 generate_hosts.py `dig apache +short` > /resolve.txt && jericho --input host.txt --log-level debug --resolve-list /resolve.txt --max-requests 10 && chmod +x validate.sh && ./validate.sh