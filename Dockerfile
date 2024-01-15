FROM python:3.11.1-slim

WORKDIR /app

# set env variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
#COPY app /app/
WORKDIR /

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
