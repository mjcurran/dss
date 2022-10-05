# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /app
#COPY requirements.txt requirements.txt
#RUN pip3 install -r requirements.txt
RUN apt-get update
RUN apt-get install -y iproute2 ethtool tcpdump
COPY . .

CMD [ "python3", "drone.py" ]