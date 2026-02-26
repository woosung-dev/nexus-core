FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN corepack enable pnpm

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install

COPY . .

EXPOSE 3001

# Run in development mode on port 3001
CMD ["pnpm", "dev", "--port", "3001"]
