# imagem base do python
FROM python:3.11-slim

# diretorio de trabalho
WORKDIR /app

# dependencias para grpc compilar pacotes
RUN apt-get update && apt-get install -y build-essential

# bibliotecas no interpretador
RUN pip install --no-cache-dir grpcio grpcio-tools

# copia codigo fonte e pasta proto
COPY . .

# ponto de entrada
CMD ["python3", "main.py"]