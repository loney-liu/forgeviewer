FROM python:3.7
RUN mkdir /www
WORKDIR /www
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pyymal
CMD [ "python", "/www/app.py" ]