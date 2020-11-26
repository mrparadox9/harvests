FROM python:3.8.6-buster

WORKDIR /app

#get via 'pip freeze > pipreqs.txt'
COPY pipreqs.txt .

RUN pip install -r pipreqs.txt

COPY /src .

CMD ["python", "harvest_bifi.py"]
