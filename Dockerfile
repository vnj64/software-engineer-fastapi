FROM python:3.10
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
COPY  app  /app/
COPY pre_start.sh /app
CMD [ "./pre_start.sh" ]