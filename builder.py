import sys
import inspect
import json
import logging
import os.path as osp

import torch
import torch.nn as nn
import torch.optim as optim

from dataset import DATASETS
from model import MODELS
from utils import prepare_data


"""
Build a dictionary of optimizer classes available in PyTorch's 'optim' module.

The dictionary's keys are strings that correspond to the names of the optimizer classes, and the values are the
optimizer classes themselves.

Returns:
    dict: A dictionary mapping optimizer class names to their corresponding classes.
"""
OPTIMIZERS = dict()
for member, obj in inspect.getmembers(sys.modules['torch.optim']):
    if inspect.isclass(obj):
        OPTIMIZERS[member] = obj


def build_model(cfg) -> nn.Module:
    """
    Builds a model from a dictionary read from a JSON file.

    Args:
        cfg (dict): A dictionary containing the model configuration.

    Returns:
        nn.Module: A PyTorch model instantiated from the configuration.

    Raises:
        KeyError: If the configuration dictionary does not have a 'type' key.
        ValueError: If the 'type' key in the configuration does not correspond
            to a registered model type in the MODELS registry.

    Example:
    >>> with open('configs/base_model.json', 'r') as f:
    >>>     data = json.load(f)
    >>> model = build_model(data['model'])
    >>> print(model)
    """
    model_cfg = cfg['model_cfg']
    model_type = cfg['type']

    if model_type not in MODELS.registry.keys():
        raise ValueError(f'Unsupported model type: `{model_type}`. '
                         f'Must be one of \n{list(MODELS.registry.keys())}')

    return MODELS[model_type](**model_cfg)

def build_dataset(data: dict) -> torch.utils.data.Dataset:
    """
    Builds a PyTorch dataset based on the configuration specified in `cfg`.

    Args:
        cfg (dict): A dictionary containing the dataset configuration information.

    Returns:
        torch.utils.data.Dataset: The PyTorch dataset built according to the configuration.

    Raises:
        ValueError: If `dataset_type` is not found in the DATASETS registry.
        
    Example:
    ```
    if __name__ == '__main__':
    with open(osp.join('configs', 'dataset_config.json'), 'r') as f:
        data = json.load(f)
    dataset = build_dataset(data['dataset'])
    print(dataset)
    ```
    """
    # Find all the dataset related keys
    dataset_keys = list(filter(lambda x: 'dataset' in x, data.keys()))
    ret = dict()
    logging.info(f'Building datasets.')
    logging.debug(f'Dataset keys: {" ,".join(k for k in dataset_keys)}')
    for key in dataset_keys:
        logging.info(f'Building dataset based on `{key}` dataset')
        dataset_cfg = data[key]['dataset_cfg']
        dataset_type = data[key]['type']
        logging.debug(f'Config:\n {dataset_cfg}')
        
        if dataset_type not in DATASETS.registry.keys():
            raise ValueError(f'Unsupported model type: `{dataset_type}`. '
                            f'Must be one of \n{list(DATASETS.registry.keys())}')
        
        if key == 'train_dataset':
            logging.debug('Calling `prepare_data` function.')
            splits, annotations = prepare_data()
            logging.info('Data preparation done.')
        dataset_cfg['split_info'] = splits
        dataset_cfg['garment_annotations'] = annotations
        ret[key] = DATASETS[dataset_type](**dataset_cfg)
        
    return ret

def build_optimizer(cfg: dict,
                    model: nn.Module):
    """
    Builds a PyTorch optimizer object using the configuration provided in the `cfg` dictionary.

    Args:
        cfg (dict): A dictionary containing the configuration for the optimizer. It should have the following keys:
            - "type": A string indicating the type of optimizer to use. This should match the name of one of the classes
                      available in the PyTorch `torch.optim` module.
            - "optimizer_cfg": A dictionary containing any additional configuration options to pass to the optimizer
                               constructor.
            - "params": The modules whose params are to be trained. If set to null in the config file (None in Python
                        format), the whole model's parameters will be added to the optimizer.
        model (nn.Module): A model, whose designated params are to be added to the parameter list of the optimizer.

    Returns:
        A PyTorch optimizer object.

    Raises:
        ValueError: If the optimizer type specified in the `cfg` dictionary is not supported. This can happen if the
                    name provided is not a valid optimizer class in the `torch.optim` module.

    Example:
        Here's an example of how to use the `build_optimizer` function to create an Adam optimizer:

        >>> cfg = {"type": "Adam", "params": None, "optimizer_cfg": {"lr": 0.001}}
        >>> optimizer = build_optimizer(cfg)
        >>> print(optimizer)
        Adam (
        Parameter Group 0
            amsgrad: False
            betas: (0.9, 0.999)
            eps: 1e-08
            lr: 0.001
            weight_decay: 0
        )
    """
    logging.info('Building optimizer.')
    optimizer_type = cfg['type']
    optimizer_cfg = cfg['optimizer_cfg']
    logging.debug(f'Config:\n{optimizer_cfg}')
    logging.debug(f'Selected modules:\n{cfg["params"]}')
    trainable_params = []
    if cfg['params'] is not None:
        for name, module in model.named_modules():
            if name in cfg['params']:
                logging.debug(f'Module: {module}')
                optimizer_cfg['params'] = trainable_params.extend(list(module.parameters()))
    else:
        trainable_params = list(filter(lambda x: x.requires_grad, model.parameters()))
    logging.debug(f'Trainable params: {optimizer_cfg["params"]}')
    if optimizer_type not in OPTIMIZERS.keys():
            raise ValueError(f'Unsupported model type: `{optimizer_type}`. '
                            f'Must be one of \n{list(OPTIMIZERS.keys())}')
            
    return OPTIMIZERS[optimizer_type](**optimizer_cfg)


if __name__ == '__main__':
    with open(osp.join('configs', 'base_model.json'), 'r') as f:
        data = json.load(f)
    logging.basicConfig(level=logging.DEBUG)
    model = build_model(cfg=data['model'])
    # for name, module in model.named_modules():
    #     if name == 'cls_head':
    #         print(module)
    #         print(f'parameters: {list(filter(lambda x: x.requires_grad, module.parameters()))}')
    opt =  build_optimizer(cfg=data['optimizer'],
                           model=model)
    print(opt)
    