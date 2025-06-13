# Use an official Node.js runtime
FROM node:18-alpine

# Create app directory
WORKDIR /app

# Copy manifest & lockfile first, install deps
COPY package*.json ./
RUN npm ci --omit=dev

# Copy the rest of the code and build
COPY . .
RUN npm run build

# Expose the listening port (Nest listens on 3001 by default)
EXPOSE 3001

# Start the app
CMD ["node", "dist/main.js"]
