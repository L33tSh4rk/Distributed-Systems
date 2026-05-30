FROM python:3.11-slim

WORKDIR /app

# instala protobuf sem cache apt/pip
RUN pip install --no-cache-dir protobuf==5.27.0

# copia arquivos do cliente
COPY . .

# comando de entrada
CMD ["python", "main.py"]