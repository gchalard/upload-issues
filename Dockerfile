FROM python:3.11-alpine

WORKDIR /app

COPY issues.py /app/

RUN pip install requests

ENTRYPOINT [ "python3", "issues.py" ]