FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.10-slim

ENV SHELL_INTERACTION=false
ENV PRETTIFY_MARKDOWN=false
ENV OS_NAME=auto
ENV SHELL_NAME=auto

ENV PYTHONUNBUFFERED=1
ENV PYTHONTHREADS=1
ENV TZ=Asia/Shanghai

WORKDIR /app
COPY . /app

#RUN apt-get update && apt-get install -y gcc

# 安装 基础工具
RUN apt-get update && \
    apt-get install -y  gcc inetutils-ping net-tools curl telnet  vim-tiny && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install litellm


RUN pip install --no-cache /app && mkdir -p /tmp/shell_gpt

# 将时区设置应用到容器内的时间服务
RUN rm -f /etc/localtime && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

VOLUME /tmp/shell_gpt

ENTRYPOINT ["sgpt"]
