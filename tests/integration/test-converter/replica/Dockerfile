FROM ubuntu:20.04 as base
WORKDIR /root/jerichosrc
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
      apt-get -y install sudo

RUN useradd -m docker && echo "docker:docker" | chpasswd && adduser docker sudo

USER docker
RUN chmod 755 /etc/apt/trusted.gpg.d/trustedkeys.gpg
RUN sudo apt-get update --fix-missing && sudo apt-get install -y apt-transport-https python3-pip python3-dev ssh software-properties-common openssh-server dnsutils
COPY . .
RUN python3 setup.py install
RUN jericho --import-endpoints tests/integration/test-cluster/endpoints.json

# Keep the container alive
RUN echo ListenAddress 0.0.0.0 >> /etc/ssh/sshd_config
RUN echo PermitEmptyPasswords yes >> /etc/ssh/sshd_config
RUN echo PermitRootLogin yes >> /etc/ssh/sshd_config
RUN echo PubkeyAuthentication no >> /etc/ssh/sshd_config
RUN passwd -d root
CMD python3 tests/integration/test-cluster/generate_hosts.py `dig apache +short` > /resolve.txt && service ssh start && jericho --delete-records && jericho --listen --log-level debug