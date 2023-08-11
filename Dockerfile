FROM python:latest

WORKDIR /src
RUN chmod 777 /src
WORKDIR /

# Installing requirements
RUN pip3 install -U pip
COPY requirements.txt .
RUN pip3 install --no-cache-dir -U -r requirements.txt

# Copying all source
COPY . .

# Starting bot
CMD ["python3", "-m", "src"]

