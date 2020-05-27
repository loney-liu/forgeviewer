FROM python:3.7
RUN mkdir /www
WORKDIR /www
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install pyyaml, eventlet, gevent, gevent-websocket 
CMD [ "python", "/www/app.py" ]