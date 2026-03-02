FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY tsconfig.json eslint.config.js ./
COPY src ./src

RUN npm run build
RUN mkdir -p dist/public && cp -r src/public/* dist/public/

EXPOSE 8081

CMD ["npm", "start"]
