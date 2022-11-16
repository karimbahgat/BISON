# syntax=docker/dockerfile:1

FROM python:3.7-slim-buster

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

RUN gunicorn core.wsgi