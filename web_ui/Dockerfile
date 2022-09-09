FROM python:3.9-slim
ENV PYTHONUNBUFFERED True

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

WORKDIR "/matching_engine_demo"

RUN git clone https://github.com/googleapis/googleapis.git
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

RUN python -m grpc_tools.protoc -I=. --proto_path=googleapis --python_out=. --grpc_python_out=. match_service.proto

RUN ls -ll

ARG port
ARG grpc_ip

ENV SERVER_PORT=$port
ENV GRPC_IP=$grpc_ip

EXPOSE $SERVER_PORT

CMD python ./main.py --port $SERVER_PORT --grpc-ip $GRPC_IP