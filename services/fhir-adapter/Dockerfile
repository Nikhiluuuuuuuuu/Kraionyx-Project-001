FROM golang:1.22-alpine@sha256:0435e09f273b9cd41ebbc9cfb28fc0e6e737c352ef2294da1bb06d338148e025 AS builder
WORKDIR /app
COPY go.mod ./
RUN go mod download
COPY . .
ARG VERSION=dev
RUN go build -trimpath -ldflags="-s -w -X main.version=${VERSION}" -o bin/fhir-adapter ./cmd/adapter

FROM alpine:3.19@sha256:494edff7360579cb513922f6c60ecab4bb267a9b8339f7962f6a78c5c31ec923
RUN apk add --no-cache curl && addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /app/bin/fhir-adapter .
RUN chown -R appuser:appgroup /app
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9090/metrics || exit 1
CMD ["./fhir-adapter"]
