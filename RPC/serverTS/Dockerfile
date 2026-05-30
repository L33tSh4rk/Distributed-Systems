# imagem base do node
FROM node:20-slim

# diretorio de trabalho
WORKDIR /app

# cache
COPY package*.json ./

# dependencias de ambiente
RUN npm install

# resto de codigo fonte e .proto
COPY . .

# porta de rede
EXPOSE 3000

# inicializacao do servidor 
CMD ["npm", "run", "dev"]