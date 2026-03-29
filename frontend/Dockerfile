FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

# Expose Vite dev server on port 3000 for Docker mapping
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
