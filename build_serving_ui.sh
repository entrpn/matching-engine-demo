#!/bin/bash

mkdir -p third_party
cp match_service.proto third_party/
cd third_party
if [ -z "googleapis/" ]; then
    git clone https://github.com/googleapis/googleapis.git
fi
pwd
python -m grpc_tools.protoc -I=. --proto_path=googleapis --python_out=. --grpc_python_out=. match_service.proto

