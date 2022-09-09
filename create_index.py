import argparse
import time

from google.cloud import aiplatform_v1beta1
from google.protobuf import struct_pb2

DEPLOYED_INDEX_ID = "ann_dog_breeds_deployed"
INDEX_DISPLAY_NAME = "index_endpoint_for_demo"

def is_index_deployed(index_endpoints):
    endpoint_deployed = False
    index_endpoint = None
    grpc_address = None
    for index_endpoint in index_endpoints:
            if index_endpoint.display_name == INDEX_DISPLAY_NAME:
                for deployed_index in index_endpoint.deployed_indexes:
                    if deployed_index.id == DEPLOYED_INDEX_ID:
                        endpoint_deployed = True
                        grpc_address = deployed_index.private_endpoints.match_grpc_address
                        break
    return endpoint_deployed, index_endpoint, grpc_address

def get_grpc_address(endpoint, parent):
    index_endpoint_client = aiplatform_v1beta1.IndexEndpointServiceClient(
    client_options=dict(api_endpoint=endpoint))

    index_endpoints = index_endpoint_client.list_index_endpoints(parent=parent)
    _, _, grpc_address = is_index_deployed(index_endpoints)
    
    return grpc_address

def deploy_index_endpoint(endpoint, parent, index_resource_name, index_endpoint_name):

    index_endpoint_client = aiplatform_v1beta1.IndexEndpointServiceClient(
    client_options=dict(api_endpoint=endpoint))

    index_endpoints = index_endpoint_client.list_index_endpoints(parent=parent)
    endpoint_deployed, index_endpoint, _ = is_index_deployed(index_endpoints)
    if not endpoint_deployed:
        deploy_ann_index = {
            "id": DEPLOYED_INDEX_ID,
            "display_name": DEPLOYED_INDEX_ID,
            "index": index_resource_name,
        }
        r = index_endpoint_client.deploy_index(
        index_endpoint=index_endpoint_name, deployed_index=deploy_ann_index
        )

        # Poll the operation until it's done successfullly.
        while True:
            if r.done():
                break
            print("Poll the operation to deploy index...")
            time.sleep(60)
        
        index_endpoint = r.result()

    print('Index deployed:',index_endpoint)


def create_index_endpoint(endpoint, parent, vpc_network_name):
    index_endpoint_client = aiplatform_v1beta1.IndexEndpointServiceClient(
    client_options=dict(api_endpoint=endpoint))

    index_endpoints = index_endpoint_client.list_index_endpoints(parent=parent)
    endpoint_exists = False
    for index_endpoint in index_endpoints:
        if index_endpoint.display_name == "index_endpoint_for_demo":
            endpoint_exists = True
            break

    if not endpoint_exists:
        index_endpoint = {
            "display_name": "index_endpoint_for_demo",
            "network": vpc_network_name,
        }
        r = index_endpoint_client.create_index_endpoint(
        parent=parent, index_endpoint=index_endpoint
        )

        print(r.result())

        index_endpoint_name = r.result().name
    else:
        index_endpoint_name = index_endpoint.name

    print("Index endpoint name:",index_endpoint_name)
    return index_endpoint_name

def create_ann_index(endpoint, parent):
    DIMENSIONS = 512
    DISPLAY_NAME = "dog_breeds_100"

    index_client = aiplatform_v1beta1.IndexServiceClient(
        client_options=dict(api_endpoint=endpoint)
    )

    indexes = index_client.list_indexes(parent=parent)
    
    print(type(indexes))
    index_exists = False
    for index in indexes:
        if index.display_name == DISPLAY_NAME:
            index_exists = True
            break

    print("Does index already exist? ",index_exists)

    if not index_exists:
        tre_ah_config = struct_pb2.Struct(
            fields={
                "leafNodeEmbeddingCount" : struct_pb2.Value(number_value=500),
                "leafNodesToSearchPercent" : struct_pb2.Value(number_value=7),
            }
        )

        algorithm_config = struct_pb2.Struct(
            fields={"treeAhConfig" : struct_pb2.Value(struct_value=tre_ah_config)}
        )

        config = struct_pb2.Struct(
            fields={
                "dimensions" : struct_pb2.Value(number_value=DIMENSIONS),
                "approximateNeighborsCount" : struct_pb2.Value(number_value=150),
                "distanceMeasureType" : struct_pb2.Value(string_value="DOT_PRODUCT_DISTANCE"),
                "algorithmConfig" : struct_pb2.Value(struct_value=algorithm_config)
            }
        )

        metadata = struct_pb2.Struct(
            fields={
                "config" : struct_pb2.Value(struct_value=config),
                "contentsDeltaUri" : struct_pb2.Value(string_value=opt.contents_delta_uri)
            }
        )

        ann_index = {
            "display_name" : DISPLAY_NAME,
            "description": "Dog breeds 512 ANN index",
            "metadata": struct_pb2.Value(struct_value=metadata),
        }

        ann_index = index_client.create_index(parent=parent, index=ann_index)
        while True:
            if ann_index.done():
                break
            print("Poll the operation to create index...\r")
            time.sleep(60)
        
        index_resource_name = ann_index.result().name
    else:
        index_resource_name = index.name
    
    print("Index resource name:",index_resource_name)

    return index_resource_name

def main(opt):
    ENDPOINT = "{}-aiplatform.googleapis.com".format(opt.region)
    PARENT = "projects/{}/locations/{}".format(opt.project_id, opt.region)
    VPC_NETWORK_NAME = "projects/{}/global/networks/{}".format(opt.project_number, opt.network)
    
    index_resource_name = create_ann_index(ENDPOINT, PARENT)
    
    index_endpoint_name = create_index_endpoint(ENDPOINT, PARENT, VPC_NETWORK_NAME)
    
    deploy_index_endpoint(ENDPOINT, PARENT, index_resource_name, index_endpoint_name)

    print("GRPC address: ",get_grpc_address(ENDPOINT, PARENT))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--region',
        type=str,
        help='GCP region',
        default='us-central1'
        )
    parser.add_argument(
        '--project-id',
        type=str,
        required=True,
        help='GCP project id'       
    )
    parser.add_argument(
        '--contents-delta-uri',
        type=str,
        required=True,
        help="The GCS folder where indexes are stored. Ex: gs://matching-engine-demo-dog-breeds"
    )
    parser.add_argument(
        '--network',
        type=str,
        required=True,
        help='The network name.'        
    )
    parser.add_argument(
        '--project-number',
        type=str,
        required=True,
        help='The project number. You can find it by going to https://console.cloud.google.com/welcome?project=<project_id>'
    )
    opt = parser.parse_args()
    main(opt)