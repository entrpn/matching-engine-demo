import argparse
import uuid
import os
import json
import zipfile
from os.path import exists

from kaggle.api.kaggle_api_extended import KaggleApi

import torchvision
from torchvision import datasets, transforms
from torch.utils.data.dataloader import default_collate
from torchvision.models.resnet import resnet18
import torch

from google.cloud import storage

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def download_dataset(data_folder):
    dataset_zip_uri = 'dog-breed-images.zip'
    if not exists(dataset_zip_uri):
        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files('eward96/dog-breed-images')
    
    os.makedirs(data_folder,exist_ok=True)
    with zipfile.ZipFile(dataset_zip_uri) as zip_ref:
        zip_ref.extractall(data_folder)

def extract_embeddings(data_folder):
    tc = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor()
    ])

    image_datasets = datasets.ImageFolder(data_folder, transform=tc)
    dataloader = torch.utils.data.DataLoader(image_datasets, batch_size=1, shuffle=False, collate_fn=lambda x: tuple(x_.to(device) for x_ in default_collate(x)))

    model = resnet18(weights='ResNet18_Weights.DEFAULT').to(device)
    layer = model._modules.get('avgpool')

    outputs = []
    def copy_embeddings(model ,input ,output):
        output = output[:,:,0,0].cpu().detach().numpy().tolist()
        outputs.append(output)
    layer.register_forward_hook(copy_embeddings)

    model.eval()
    image_paths = []
    for i, (images, _) in enumerate(dataloader, 0):
         _ = model(images)
         image_paths.append(dataloader.dataset.samples[i][0])

    list_embeddings = [item for sublist in outputs for item in sublist]
    return dict(zip(image_paths, list_embeddings))

def main(opt):
    data_folder = 'data'
    data_file = 'data.json'
    data_file_path = f'{data_folder}/{data_file}'
    
    download_dataset(data_folder)
    
    if not exists(data_file_path):
        embeddings_dict = extract_embeddings(data_folder)

        with open(data_file_path,'w') as f:
            for key in embeddings_dict.keys():
                uniq_id = key.split("/")[-1].split(".")[0]
                f.write('{"id":"' + uniq_id + '",')
                f.write('"embedding":[' + ",".join(str(x) for x in embeddings_dict[key]) + "]}")
                f.write("\n")
    
    storage_client = storage.Client()

    bucket_name = f'matching-engine-demo-dog-breeds{str(uuid.uuid4())[:8]}'
    bucket = storage.Bucket(storage_client, bucket_name)

    if not bucket.exists():
        bucket = storage_client.create_bucket(bucket_name, location=opt.region)

    blob = bucket.blob(data_file)
    blob.upload_from_filename(f'{data_folder}/{data_file}')

    print(f"Bucket gs://{bucket_name} was created")

    #create_metadata(data_folder, f"gs://matching-engine-demo-dog-breeds")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--region',
        type=str,
        help='GCP region',
        default='us-central1'
    )
    opt = parser.parse_args()
    main(opt)