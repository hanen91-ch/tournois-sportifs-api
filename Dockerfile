FROM python:3.14
LABEL maintainer="hanen@bdeb.qc.ca"
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt
COPY . /app
CMD [ "python", "./app.py" ]