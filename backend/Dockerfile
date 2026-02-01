FROM node:20-alpine

WORKDIR /app

# Install system dependencies (Prisma needs OpenSSL)
RUN apk add --no-cache openssl

# Install dependencies first (for better caching)
COPY package*.json ./
RUN npm ci

# Copy prisma schema and generate client
COPY prisma ./prisma
RUN npx prisma generate

# Copy rest of source
COPY . .

# Build TypeScript
RUN npm run build

EXPOSE 3001

# Start server
CMD ["npm", "start"]
