FROM osgeo/gdal:ubuntu-small-3.6.3

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt .
RUN apt-get update && \
    apt-get upgrade -y

RUN apt-get install -y python3-pip cmake libbz2-dev libboost-all-dev
RUN apt-get install -y libxml2-dev libxslt-dev
RUN apt-get build-dep python3-lxml

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --upgrade wheel

RUN pip install -r requirements.txt