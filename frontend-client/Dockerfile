FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN corepack enable pnpm

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install

COPY . .

EXPOSE 3000

# Run in development mode
CMD ["pnpm", "dev"]
