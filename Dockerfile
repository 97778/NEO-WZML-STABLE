# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

FROM pro97775/neo-wzml:latest-v1.1

WORKDIR /usr/src/app

RUN chmod 777 /usr/src/app

COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
