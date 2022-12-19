# syntax=docker/dockerfile:1

FROM python:3.7-slim-buster

WORKDIR /opt/boundarylookup

COPY . /opt/boundarylookup

RUN apt-get update &&\
    apt-get install -y git &&\
    pip3 install -r requirements.txt &&\
    apt-get remove -y git &&\
    apt autoremove -y &&\
    python manage.py collectstatic

CMD ["sh run.sh"]
