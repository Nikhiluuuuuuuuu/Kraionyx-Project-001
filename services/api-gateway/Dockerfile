FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o bin/api-gateway ./cmd/server

FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/bin/api-gateway .
EXPOSE 8443
CMD ["./api-gateway"]
