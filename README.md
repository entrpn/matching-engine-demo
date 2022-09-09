# Matching Engine Demo
![](./images/matching_engine_demo.gif)

In this demo, we'll create a dog breed search using Kaggle's dog breeds [dataset](https://www.kaggle.com/datasets/eward96/dog-breed-images) and GCP's [Matching Engine](https://cloud.google.com/vertex-ai/docs/matching-engine/overview).

## Setup

1. After cloning this repo, do a `pip install -r requirements.txt`.

1. We'll need to download the dataset and create the embeddings. If you haven't downloaded your Kaggle [API credentials](https://www.kaggle.com/docs/api), do it now. Now run.

    ```python
    python extract_embeddings.py
    ```

    This script downloads the Kaggle dog breeds dataset, creates embeddings using a pretrained pytorch Resnet-18 model and uploads them to a GCS bucket. At the end of the script, you'll see a message `Bucket gs://{bucket_name} was created`. Keep this handy as we'll be using this in another step.

1. Next, we'll need to set up a VPC as it is required by Matching Engine. Run `network_setup.sh`.

    ```bash
    ./network_setup.sh -n matching-engine-demo -r matching-engine-peering -p <project_id>
    ```

1. Now it is time to create the index. Run `create_index.py` and use the bucket name from one of the steps above as the `contents-delta-uri` parameter. This operation will take a while as it creates the index and endpoint in Matching Engine.

    ```python
    python create_index.py --project-id <project_id> --contents-delta-uri gs://<bucket_name> --network matching-engine-demo --project-number <project_number>
    ```

    When the script is finished, it will print the grpc ip address which we will need in the next step.

1. To query an index, we'll need to use grpc. This is embedded inside a gradio app in the `web_ui folder`. `cd` into the folder and build the image. We'll run this image in Cloud Run.

    ```shell
    cd web_ui
    mkdir images
    find ../data/ -name '*.jpg' -exec cp -t images/ {} +
    docker build . --build-arg port=80 --build-arg grpc_ip=<grpc_ip> -t gcr.io/<project_id>/matching-engine-ui:latest
    docker push gcr.io/<project_id>/matching-engine-ui:latest
    ```

    The app won't work in our local environment because the endpoint is only accessible in the same VPC. For this we need to create a VPC connector for the Cloud Run app to have access.

    ```shell
    gcloud services enable vpcaccess.googleapis.com
    gcloud compute networks vpc-access connectors create matching-engine-connector --network matching-engine-demo --region us-central1 --range 10.8.0.0/28
    gcloud compute networks vpc-access connectors describe matching-engine-connector --region us-central1
    ```

    Now deploy the app

    ```shell
    gcloud run deploy --port 80 matching-engine-ui --image gcr.io/<project_id>/matching-engine-ui:latest --vpc-connector matching-engine-connector --timeout 3600 --region us-central1 --cpu=4 --memory 4Gi
    ```
