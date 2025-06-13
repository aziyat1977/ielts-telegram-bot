# Use Node 20 so engine requirements are satisfied
FROM node:20-alpine AS build

WORKDIR /app

# 1️⃣ Copy only package manifests
COPY package*.json ./

# 2️⃣ Install all deps (including dev) so `nest` is available
RUN npm install

# 3️⃣ Copy the rest of your source and build it
COPY . .
RUN npm run build

# 4️⃣ Remove devDependencies for the final image
RUN npm prune --production

# —— now create the slim runtime image —— 
FROM node:20-alpine

WORKDIR /app

# 5️⃣ Copy built files + prod deps from the build stage
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist

# 6️⃣ Expose the port and run
EXPOSE 3001
CMD ["node", "dist/main.js"]
