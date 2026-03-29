FROM node:20-alpine

WORKDIR /app

COPY node-backend/package*.json ./
RUN npm install

COPY node-backend/src ./src
COPY node-backend/.env.example ./.env.example

EXPOSE 5050

CMD ["npm", "run", "start"]
