FROM debian
WORKDIR /code
RUN apt update
RUN sudo apt install libopenmpi-dev python3-pip python3-dev  -y
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD "echo 127.0.0.1 |python3 jericho/jericho.py "