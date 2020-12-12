FROM python:3.7-alpine

COPY . /
RUN pip install -r requirements.txt
RUN mkdir -p /root/morizon_analyzer/logs
ENTRYPOINT ["python", "."]
