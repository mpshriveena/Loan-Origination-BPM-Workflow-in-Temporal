FROM python:3.10
WORKDIR /worker
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y sqlite3
COPY . .
CMD ["sh", "-c", "python3 init.py && python3 register_activity.py"]

