FROM golang:alpine AS builder

LABEL stage=gobuilder

ENV CGO_ENABLED 0

RUN apk update --no-cache && apk add --no-cache tzdata

WORKDIR /build

ADD go.mod .
ADD go.sum .
RUN go mod download
COPY . .
# 编译 main_function/function.go
RUN go build -o /app/function_exec main_function/function.go
# 编译 proxy.go
RUN go build -o /app/proxy


FROM ubuntu:20.04

RUN sed -i s@/archive.ubuntu.com/@/mirrors.aliyun.com/@g /etc/apt/sources.list
RUN apt-get clean

RUN apt-get update && \
    apt-get install -y schedtool && \
    apt-get install -y util-linux && \
    apt-get install -y python3
# For running sudo schedtool 
RUN apt-get install -y sudo

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=builder /usr/share/zoneinfo/Asia/Shanghai /usr/share/zoneinfo/Asia/Shanghai
ENV TZ Asia/Shanghai

WORKDIR /app
# 从构建阶段复制编译后的二进制文件
COPY --from=builder /app/proxy /app/proxy
COPY --from=builder /app/function_exec /app/function_exec

CMD ["./proxy"]
