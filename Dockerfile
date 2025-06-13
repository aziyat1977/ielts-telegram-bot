# 1) use Node 20 so @nestjs/core (which needs “node >=20”) will install
FROM node:20-alpine

# 2) set working directory
WORKDIR /app

# 3) copy only manifest & lockfile first (caching)
COPY package*.json ./

# 4) install prod deps, regenerating lock as needed
RUN npm install --omit=dev

# 5) copy everything else
COPY . .

# 6) build your Nest app
RUN npm run build

# 7) expose and run
EXPOSE 3001
CMD ["node", "dist/main.js"]
