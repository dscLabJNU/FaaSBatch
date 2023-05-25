# recommend not to use the alpine one, it lacks lots of dependencies
# the slim one ocuppies about 2x space compared to alpine one
# FROM python:3.7-alpine
FROM python:3.7-slim

COPY pip.conf /etc/pip.conf
RUN sed -i "s@http://deb.debian.org@https://mirrors.ustc.edu.cn/@g" /etc/apt/sources.list && rm -Rf /var/lib/apt/lists/* && apt-get update
# fulfill the structure requirement of proxy
RUN mkdir /proxy

# copy libs
COPY *.py /proxy/
COPY requirements.txt /proxy/requirements.txt
WORKDIR /proxy

# proxy server runs under port 5000
EXPOSE 5000

RUN apt-get clean
RUN apt-get update
RUN pip3 install --no-cache-dir -r requirements.txt

CMD [ "python3", "/proxy/proxy.py" ]
