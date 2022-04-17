FROM ubuntu:20.04 as base
WORKDIR /root/jerichosrc
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update --fix-missing && apt-get install -y apt-transport-https python3-pip python3-dev ssh software-properties-common dnsutils
COPY . .
RUN python3 setup.py install
RUN cat /dev/zero | ssh-keygen -q -N ""
RUN echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config
RUN echo "    UserKnownHostsFile=/dev/null" >> /etc/ssh/ssh_config

CMD python3 tests/integration/test-converter/generate_hosts.py `dig apache +short` > /resolve.txt && jericho --delete-records && jericho --add-server=`dig +short jericho_replica` && chmod +x tests/integration/test-converter/run-and-verify.sh && bash -c ./tests/integration/test-converter/run-and-verify.sh

