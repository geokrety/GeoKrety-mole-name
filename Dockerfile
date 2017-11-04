FROM ubuntu:xenial
MAINTAINER Mathieu Alorent <github@kumy.net>

RUN apt-get update \
    && apt-get install -y \
        python3-pip \
        python3-dev \
        build-essential \
    && apt-get clean \
    && rm -fr /var/lib/apt/lists

COPY requirements.txt /tmp/
RUN pip3 install --requirement /tmp/requirements.txt
COPY . /opt/flask

WORKDIR /opt/flask
EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "--reload", "app.main:app"]
