FROM ubuntu:22.04

RUN mkdir /code
WORKDIR /code

RUN apt-get -y update --fix-missing
RUN apt-get -y install curl python3 python3-pip unzip wget
RUN ln -s /usr/bin/python3 /usr/bin/python

# Install Git
RUN apt-get -y install git

# Python requirements
COPY requirements.txt /code/
RUN pip install -r requirements.txt