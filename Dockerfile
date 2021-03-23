FROM python:3.7-alpine

COPY . /morizon_analyzer
WORKDIR /morizon_analyzer
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "."]
