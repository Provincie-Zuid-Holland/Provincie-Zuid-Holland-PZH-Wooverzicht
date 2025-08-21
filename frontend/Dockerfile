# Step 1: Build the app
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Step 2: Serve the app using Next.js built-in server
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Install ONLY production dependencies (fresh, clean install)
COPY package*.json ./
RUN npm install --production && npm cache clean --force

# Copy built application files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/next.config.js ./next.config.js

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001
USER nextjs

EXPOSE 3000

CMD ["npm", "start"]