# Build stage
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Build args
ARG VITE_API_BASE_URL
ARG VITE_API_KEY
ARG IMAGE_TAG=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_TIME

# Set as env vars for build
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_KEY=$VITE_API_KEY
ENV VITE_IMAGE_TAG=$IMAGE_TAG
ENV VITE_GIT_COMMIT=$GIT_COMMIT
ENV VITE_BUILD_TIME=$BUILD_TIME

# Debug: Print env vars during build
RUN echo "=== Build Environment ==="
RUN echo "VITE_API_BASE_URL: $VITE_API_BASE_URL"
RUN echo "VITE_API_KEY: ${VITE_API_KEY:+<set>}${VITE_API_KEY:-<not set>}"
RUN echo "NODE_ENV: ${NODE_ENV:-production}"
RUN echo "IMAGE_TAG: $IMAGE_TAG"
RUN echo "GIT_COMMIT: $GIT_COMMIT"
RUN echo "BUILD_TIME: $BUILD_TIME"
RUN echo "========================="

# Build for production
RUN npm run build

# Debug: Verify built files contain the correct configuration
RUN echo "=== Checking Built Files ==="
RUN echo "Searching for API configuration in built files..."
RUN find dist -name "*.js" -type f -exec grep -l "gw.tnight.xyz" {} \; | head -3 || echo "⚠️  WARNING: API URL not found in JS files!"
RUN echo "Searching for 'import.meta.env' references..."
RUN grep -r "VITE_API" dist/ 2>/dev/null | head -5 || echo "No VITE_API references found (this is expected if properly compiled)"
RUN echo "============================"

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
