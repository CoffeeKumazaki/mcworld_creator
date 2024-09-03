FROM python:3.10

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt .
RUN apt-get update && \
    apt-get upgrade -y

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --upgrade wheel

RUN pip install -r requirements.txt