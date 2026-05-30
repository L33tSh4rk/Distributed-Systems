# build
FROM node:20-alpine AS builder

WORKDIR /usr/src/app

# otimização de cache
COPY package*.json ./
RUN npm ci

# codigo fonte e conf
COPY tsconfig.json ./
COPY src/ ./src/

# Executa compilador ts
RUN npm run build

# produção
FROM node:20-alpine

WORKDIR /usr/src/app

COPY package*.json ./
# instala dependencias necessarias
RUN npm ci --omit=dev

# copia codigo
COPY --from=builder /usr/src/app/dist ./dist


# força copia manual para dir compilado
COPY src/proto/*.proto ./dist/proto/

# var de ambiente padrão
ENV PORT=3000

# documenta porta para dev
EXPOSE 3000

CMD ["node", "dist/server.js"]