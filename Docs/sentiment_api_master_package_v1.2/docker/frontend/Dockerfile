FROM node:20-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* frontend/pnpm-lock.yaml* /app/

# Install deps (supports npm; if using pnpm/yarn, adjust)
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend /app

ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000

CMD ["npm", "run", "dev", "--", "-p", "3000"]
