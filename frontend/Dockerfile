# ---- Base Layer ----
FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

# ---- Development Target ----
FROM base AS development
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- Build Production Assets ----
FROM base AS builder
COPY . .
RUN npm run build

# ---- Production Target ----
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html

# Optional: Add custom nginx configuration for routing
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
