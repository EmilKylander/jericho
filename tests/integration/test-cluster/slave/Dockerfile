FROM ubuntu:21.10 as base
WORKDIR /app
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y apt-transport-https
RUN apt install libopenmpi-dev python3-pip python3-dev ssh software-properties-common openssh-server  -y
RUN pip3 install pyyaml aiohttp sqlalchemy python-Levenshtein-wheels mpi4py bs4 aioretry
RUN echo 'btl_base_warn_component_unused = 0' > /etc/openmpi/openmpi-mca-params.conf 
COPY . .
RUN python3 setup.py install
RUN jericho --import-endpoints data/endpoints.json

# Keep the container alive
RUN echo ListenAddress 0.0.0.0 >> /etc/ssh/sshd_config
RUN echo PermitEmptyPasswords yes >> /etc/ssh/sshd_config
RUN echo PermitRootLogin yes >> /etc/ssh/sshd_config
RUN echo PubkeyAuthentication no >> /etc/ssh/sshd_config
RUN passwd -d root
CMD export RDMAV_FORK_SAFE=0 && service ssh start && tail -f /dev/null