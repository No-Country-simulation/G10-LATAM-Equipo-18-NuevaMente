# Stage 1: Build Angular application
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build -- --configuration=production

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copiar bundle de producción Angular al directorio público de Nginx
COPY --from=build /app/dist/nuevamente-frontend/browser /usr/share/nginx/html

# Copiar configuración de Nginx con reverse proxy hacia FastAPI
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
