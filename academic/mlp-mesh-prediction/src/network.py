"""Small CPU MLP and training-only coordinate scaling."""
import numpy as np
import torch
from torch import nn
from src.common import ROOT

class MeshMLP(nn.Module):
    def __init__(self,output_size,hidden=(64,64)):
        super().__init__()
        self.layers=nn.Sequential(nn.Linear(4,hidden[0]),nn.Tanh(),
            nn.Linear(hidden[0],hidden[1]),nn.Tanh(),nn.Linear(hidden[1],output_size))
    def forward(self,mu):
        return self.layers(mu)

class Predictor:
    def __init__(self,path=None):
        package=torch.load(path or ROOT/'models/mlp.pt',map_location='cpu',weights_only=True)
        torch.set_num_threads(package['threads'])
        self.model=MeshMLP(package['output_size'],package['hidden'])
        self.model.load_state_dict(package['state_dict']);self.model.eval()
        self.mean=np.asarray(package['input_mean'])
        self.std=np.asarray(package['input_std'])
        self.displacement_scale=package['displacement_scale']
        self.package=package

    def predict(self,mu):
        normalized=(np.asarray(mu)-self.mean)/self.std
        with torch.inference_mode():
            result=self.model(torch.tensor(normalized,dtype=torch.float32).reshape(1,4))
        return result.numpy().astype(np.float64).reshape(-1,2)*self.displacement_scale
