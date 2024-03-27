FROM alpine:3.19

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN apk add --update --no-cache py3-pip

WORKDIR /usr/src/app
COPY grass.py .
COPY requirements.txt .

RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple  --no-cache-dir -r ./requirements.txt --break-system-packages

CMD [ "python", "./grass.py" ]
EXPOSE 80
