FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL
ARG VITE_YANDEX_MAPS_KEY
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_YANDEX_MAPS_KEY=$VITE_YANDEX_MAPS_KEY
RUN npm run build

FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
