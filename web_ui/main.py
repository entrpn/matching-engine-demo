from unicodedata import name
import argparse
import numpy as np
import torch
from torchvision import transforms
from torchvision.models.resnet import resnet18

import grpc
import match_service_pb2
import match_service_pb2_grpc

import gradio as gr

def main(opt):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    preprocess = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor()
    ])

    model = resnet18(weights='ResNet18_Weights.DEFAULT').to(device)
    layer = model._modules.get('avgpool')

    def predict(inp):
        outputs = []
        def copy_embeddings(model, input, output):
            output = output[:,:,0,0].cpu().detach().numpy()
            outputs.append(output)
        layer.register_forward_hook(copy_embeddings)
        model.eval()
        inp = preprocess(inp)
        inp = inp[None, :]
        print(inp.shape)
        with torch.no_grad():
            model(inp)
        list_embeddings = [item for sublist in outputs for item in sublist]
        list_embeddings = np.array(list_embeddings)[0]
        input_embeddings = outputs[0]
        embedding_img = np.array(input_embeddings)
        embedding_img = embedding_img / np.max(embedding_img)
        embedding_img = 255 * embedding_img
        embedding_img = embedding_img.astype(np.uint8)
        outputs.clear()

        channel = grpc.insecure_channel("{}:10000".format(opt.grpc_ip))
        stub = match_service_pb2_grpc.MatchServiceStub(channel)

        request = match_service_pb2.MatchRequest()
        request.deployed_index_id = "ann_dog_breeds_deployed"
        for val in list_embeddings:
            request.float_val.append(val)
        
        response = stub.Match(request)
        print(response)

        return list_embeddings, embedding_img

    gr.Interface(fn=predict,
                inputs=gr.Image(type='pil'),
                outputs=[gr.Textbox(),"image"]).launch(share=False, 
                                                debug=False, 
                                                server_name='0.0.0.0', 
                                                server_port=opt.port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--grpc-ip',
        type=str,
        help='GRPC ip of matching engine endpoint',
    )
    parser.add_argument(
        '--port',
        type=int,
        help='Port to run the gradio app',
    )

    opt = parser.parse_args()
    main(opt)