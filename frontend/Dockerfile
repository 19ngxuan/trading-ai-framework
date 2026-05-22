FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html ./
COPY tsconfig.json tsconfig.node.json vite.config.ts ./
COPY src ./src

EXPOSE 5173

CMD ["npm", "run", "dev"]
