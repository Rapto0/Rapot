FROM node:20.20.2-alpine AS base
RUN npm install --global npm@10.9.9

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the application
ARG NEXT_PUBLIC_API_URL=/api
ARG API_PROXY_TARGET=http://api:8000
ARG HEALTH_PROXY_TARGET=http://bot:5000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    API_PROXY_TARGET=$API_PROXY_TARGET \
    HEALTH_PROXY_TARGET=$HEALTH_PROXY_TARGET \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverage output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
