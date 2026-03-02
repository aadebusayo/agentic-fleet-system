FROM golang:1.22-alpine AS build

WORKDIR /src

COPY go.mod ./
COPY cmd ./cmd
COPY internal ./internal

RUN go build -o /bin/agent-fleet ./cmd/server

FROM alpine:3.20

WORKDIR /app
COPY --from=build /bin/agent-fleet /usr/local/bin/agent-fleet

EXPOSE 8082

CMD ["/usr/local/bin/agent-fleet"]
