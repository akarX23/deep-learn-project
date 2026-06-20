FROM oven/bun:latest

WORKDIR /app

COPY react_ui/package.json /app/package.json

RUN bun install --frozen-lockfile

COPY react_ui /app

# RUN bun run build

CMD ["bun", "run", "dev", "--host", "0.0.0.0", "--port", "3000"]