FROM ubuntu:21.10 as base
WORKDIR /app
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y apt-transport-https
RUN apt install libopenmpi-dev python3-pip python3-dev ssh software-properties-common -y
RUN pip3 install pyyaml aiohttp sqlalchemy python-Levenshtein-wheels mpi4py bs4 aioretry
RUN echo 'btl_base_warn_component_unused = 0' > /etc/openmpi/openmpi-mca-params.conf
COPY . .
RUN python3 setup.py install
RUN jericho --import-endpoints tests/integration/test-cluster/endpoints.json
RUN cat /dev/zero | ssh-keygen -q -N ""
RUN echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config
RUN echo "    UserKnownHostsFile=/dev/null" >> /etc/ssh/ssh_config

CMD chmod +x tests/integration/test-cluster/run-and-verify.sh && bash -c ./tests/integration/test-cluster/run-and-verify.sh

