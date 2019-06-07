# -*- coding: utf-8 -*-
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import numpy as np
from config import net_config

class MLP(nn.Module):
    '''
    '''
    def __init__(self, in_features, layer_num, layers):
        super(MLP, self).__init__()
        self.in_features = in_features
        self.mlp = self._make_layers(layer_num, layers)
    
    def _make_layers(self, layer_num, layers):
        mlp = []
        mlp.append(nn.Linear(self.in_features, layers[0]))
        for i in range(1, layer_num):
            mlp.append(nn.Linear(layers[i - 1], layers[i]))
            #TODO: add activation function here if necessary
        
        return nn.Sequential(*mlp)

    def forward(self, x):
        out = self.mlp(x)

        return out


class CSVAE(nn.Module):
    '''
    Conditional Subspace VAE
    Args:
        x: Tensor (batch, 3)
        y: Tensor (batch, 1)
    '''
    def __init__(self, mode='train',
                    MU_1=net_config['MU_1'], MU_2_0=net_config['MU_2_0'], MU_2_1=net_config['MU_2_1'], 
                    SIG_1=net_config['SIG_1'], SIG_2_0=net_config['SIG_2_0'], SIG_2_1=net_config['SIG_2_1']):
        super(CSVAE, self).__init__()
        self.mode = mode
        self.MU_1 = MU_1
        self.MU_2_0 = MU_2_0
        self.MU_2_1 = MU_2_1
        self.SIG_1 = SIG_1
        self.SIG_2_0 = SIG_2_0
        self.SIG_2_1 = SIG_2_1
        self.useCUDA = torch.cuda.is_available()
        self.enc1 = MLP(net_config['in_features1'], net_config['in_layer_num1'], net_config['in_layers1'])
        self.enc2 = MLP(net_config['in_features2'], net_config['in_layer_num2'], net_config['in_layers2'])
        self.dec = MLP(net_config['out_features'], net_config['out_layer_num'], net_config['out_layers'])
        self.encMuZ = nn.Linear(net_config['in_layers1'][-1], net_config['z_dim'])
        self.encSigmaZ = nn.Linear(net_config['in_layers1'][-1], net_config['z_dim'])
        self.encMuW = nn.Linear(net_config['in_layers2'][-1], net_config['w_dim'])
        self.encSigmaW = nn.Linear(net_config['in_layers2'][-1], net_config['w_dim'])
        self.decOut = nn.Linear(net_config['out_layers'][-1], net_config['in_features1'])

    def re_parm(self, mu, sigma, dim):
        if self.useCUDA:
            eps = Variable(torch.randn(sigma.size(0), dim).cuda())
        else:
            eps = Variable(torch.randn(sigma.size(0), dim))
        
        return mu + sigma * eps

    def encode(self, x, y):
        xy = torch.cat([x, y], dim=1)
        x = Variable(x)
        # y = Variable(y)
        xy = Variable(xy)
        x1 = self.enc1(x)
        x2 = self.enc2(xy)
        mu_z = self.encMuZ(x1)
        sigma_z =  self.encSigmaZ(x1)
        z = self.re_parm(mu_z, sigma_z, net_config['z_dim'])

        if self.mode=='train':
            y_idx_0 = y==0
            y_idx_1 = y==1
            mu_w_0 = self.encMuW(x2[y_idx_0])
            mu_w_1 = self.encMuW(x2[y_idx_1])
            sigma_w_0 = self.encSigmaW(x2[y_idx_0])
            sigma_w_1 = self.encSigmaW(x2[y_idx_1])
            mu_w = self.encMuW(x2)
            sigma_w = self.encSigmaW(x2)
            w = self.re_parm(mu_w, sigma_w, net_config['w_dim'])

            return z, w, mu_z, mu_w_0, mu_w_1, sigma_z, sigma_w_0, sigma_w_1

        else:
            mu_w = self.encMuW(x2)
            sigma_w = self.encSigmaW(x2)
            w = self.re_parm(mu_w, sigma_w, net_config['w_dim'])

            return z, w, mu_z, mu_w, sigma_z, sigma_w

    def decode(self, z, w):
        '''
        Args:
            z: Tensor (batch, z_dim)
            w: Tensor (batch, w_dim)
        '''
        zw = torch.cat([z, w], dim=1)
        zw = self.dec(zw)
        zw = self.decOut(zw)

        return zw

    def forward(self, x, y):
        if self.mode == 'train':
            z, w, mu_z, mu_w_0, mu_w_1, sigma_z, sigma_w_0, sigma_w_1 = self.encode(x, y)
            out = self.decode(z, w)

            return z, w, mu_z, mu_w_0, mu_w_1, sigma_z, sigma_w_0, sigma_w_1
        
        else:
            z, w, mu_z, mu_w, sigma_z, sigma_w = self.encode(x, y)
            out = self.decode(z, w)

            return z, w, mu_z, mu_w, sigma_z, sigma_w, out

    def loss(self, rec_x, x, y, mu_z, mu_w, sigma_z, sigma_w):
        KLZ = 0
        KLW0 = 0
        KLW1 = 0
        rec_loss = 0

        return KLZ + KLW0/torch.sum(y==0) + KLW1/torch.sum(y==1) + rec_loss






