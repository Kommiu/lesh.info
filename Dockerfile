FROM python:3.7-slim
RUN apt-get update && apt-get install -y bash curl
WORKDIR /usr/local/src/
COPY . /usr/local/src
ENV PYTHONPATH=/usr/local/src/

RUN pip install --no-cache -r /usr/local/src/requirements.txt
