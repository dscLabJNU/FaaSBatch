FROM python:3.7-slim

COPY pip.conf /etc/pip.conf
RUN mkdir /proxy

# copy libs
COPY *.py /proxy/
COPY requirements.txt /proxy/requirements.txt
WORKDIR /proxy

# proxy server runs under port 5000
EXPOSE 5000

RUN pip3 install -r requirements.txt

CMD [ "python3", "/proxy/proxy.py" ]
