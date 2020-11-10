FROM python:3.9.0-buster

WORKDIR /app

#get via 'pipp freeze > pipreqs.txt'
COPY pipdeps.txt .

RUN pip install -r pipreqs.txt

