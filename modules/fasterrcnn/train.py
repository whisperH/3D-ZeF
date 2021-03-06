import os
import utils
import datetime
import pickle as pkl
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import transforms as T

from torch.optim import lr_scheduler
from torchvision import datasets, models, transforms
from engine import train_one_epoch, evaluate
from custom_dataset import CustomDataset
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor


def get_transform(train):
    transforms = []
    transforms.append(T.ToTensor())
    if train:
        transforms.append(T.RandomHorizontalFlip(0.5))
    return T.Compose(transforms)

def initializeModel(pretrained, num_classes):
    """
    Loads the Faster RCNN ResNet50 model from torchvision, and sets whether it is COCO pretrained, and adjusts the head box predictor to our number of classes.

    Input:
        pretrained: Whether to use a CoCo pretrained model
        num_classes: How many classes we have:

    Output:
        model: The initialized PyTorch model
    """

    # Load model
    model = models.detection.fasterrcnn_resnet50_fpn(pretrained=pretrained)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    return model

def writeCOCOtoTXT(stats, output_file, cat):
    """
    Writes the provided MS COCO metric results for a given cateogry to a txt file
    Input:
        - stats: List containing the results for the 12 MS COCO metric
        - output-file: Path to the output file
        - cat: Cateogry which has been analyzed

    """

    with open(output_file, "w") as f:
        f.write("Category:\t{}\n".format(cat))
        f.write("Average Precision  (AP) @[ IoU=0.50:0.95 | area=   all | maxDets=100 ] = {}\n".format(stats[0]))
        f.write("Average Precision  (AP) @[ IoU=0.50      | area=   all | maxDets=100 ] = {}\n".format(stats[1]))
        f.write("Average Precision  (AP) @[ IoU=0.75      | area=   all | maxDets=100 ] = {}\n".format(stats[2]))
        f.write("Average Precision  (AP) @[ IoU=0.50:0.95 | area= small | maxDets=100 ] = {}\n".format(stats[3]))
        f.write("Average Precision  (AP) @[ IoU=0.50:0.95 | area=medium | maxDets=100 ] = {}\n".format(stats[4]))
        f.write("Average Precision  (AP) @[ IoU=0.50:0.95 | area= large | maxDets=100 ] = {}\n".format(stats[5]))
        f.write("Average Recall     (AR) @[ IoU=0.50:0.95 | area=   all | maxDets=1   ] = {}\n".format(stats[6]))
        f.write("Average Recall     (AR) @[ IoU=0.50:0.95 | area=   all | maxDets=10  ] = {}\n".format(stats[7]))
        f.write("Average Recall     (AR) @[ IoU=0.50:0.95 | area=   all | maxDets=100 ] = {}\n".format(stats[8]))
        f.write("Average Recall     (AR) @[ IoU=0.50:0.95 | area= small | maxDets=100 ] = {}\n".format(stats[9]))
        f.write("Average Recall     (AR) @[ IoU=0.50:0.95 | area=medium | maxDets=100 ] = {}\n".format(stats[10]))
        f.write("Average Recall     (AR) @[ IoU=0.50:0.95 | area= large | maxDets=100 ] = {}".format(stats[11]))
        f.write("\n\n")

def train(num_epochs, cam):
    """
    Trains a Faster RCNN model for detecting zebrafish.

    *************************************************
    1. Download the 3D-ZeF folder (14.0 GB) from motchallenge.net/data/3D-ZeF20/

    2. Unzip the '3DZeF20.zip' folder into the '3d-zef' main folder, such that you get the following structure:
        /your/path/3d-zef/3DZeF20/

    3. Create a conda environment from 'environment.yml'
        $ conda env create --file environment.yml
        This will create a simple conda environment named "3dzef" with pytorch, torchvision and pycocotools.

    5. Activate the conda environment

    6. Run the script 3d-zef/modules/dataset_processing/headers2GTFiles.sh

    7. Ensure that your groundtruth files have headers:
        Look for '/3d-zef/3DZeF20/train/ZebraFish-01/gt/gt.txt'
        The expected header should be:
            frame,id,3d_x,3d_y,3d_z,camT_x,camT_y,camT_left,camT_top,camT_width,camT_height,camT_occlusion,camF_x,camF_y,camF_left,camF_top,camF_width,camF_height,camF_occlusion

    8. Run the script '3d-zef/modules/dataset_processing/gatherTrainImgs.py' in order to create symlinks of all the training images into a top and front folder as well as simplified and gathered ground truth files
        The data will be placed under 3d-ZeF/3DZeF20/train/All/

    9. Run the train.py file to train a fasterrcnn model for 1 epoch
    *************************************************
    """

    # Train the model
    train_batchsize = 8
    lr = 0.005
    momentum = 0.9
    weight_decay = 0.0005
    step_size = 30
    gamma = 0.1
    pretrained = True
    timeStamp =  datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")

    output_folder = os.path.join("..", "Sessions", timeStamp)
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    for dir_name in ["models", "info"]:
        dir_path = os.path.join(output_folder, dir_name)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)

    settings_path = os.path.join(output_folder, "info", "settings.txt")
    with open(settings_path, "w") as f:
        f.write("Max epochs: {}\n".format(num_epochs))
        f.write("Training batch size: {}\n".format(train_batchsize))
        f.write("Initial learning rate: {}\n".format(lr))
        f.write("Momentum: {}\n".format(momentum))
        f.write("Weight decay: {}\n".format(weight_decay))
        f.write("LR step size: {}\n".format(step_size))
        f.write("LR gamma:  {}\n".format(gamma))
        f.write("pretrained model: {}\n".format(pretrained))

    # train on the GPU or on the CPU, if a GPU is not available
    if torch.cuda.is_available():
        device = torch.device('cuda:7')
        print("Using GPU")
    else:
        print("WARNING: Using CPU")
        device = torch.device('cpu')

    # our dataset has two classes only - background and zebrafish
    num_classes = 2

    model = initializeModel(pretrained, num_classes)

    # use our dataset and defined transformations
    dataset_train = CustomDataset('/home/data/HJZ/3DZeF20/train/all', cam=cam, transforms=get_transform(train=True))

    # define training and validation data loaders
    data_loader_train = torch.utils.data.DataLoader(
        dataset_train, batch_size=train_batchsize, shuffle=True, num_workers=0,
        collate_fn=utils.collate_fn)

    # move model to the device (GPU/CPU)
    model.to(device)

    # construct an optimizer
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=lr, momentum=momentum, weight_decay=weight_decay)
    # and a learning rate scheduler
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer,
                                                   step_size=step_size,
                                                   gamma=gamma)

    for epoch in range(num_epochs):
        # train for one epoch, printing every 10 iterations
        training_info = train_one_epoch(model, optimizer, data_loader_train, device, epoch, print_freq=100)
        # update the learning rate
        lr_scheduler.step()

        model_path = os.path.join(output_folder, "models", 'faster_RCNN_resnet50_{0}_{1}_epochs.tar'.format(str(epoch+1), str(cam)))
        torch.save({
                'epoch': epoch+1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                },model_path)

        training_info_path = os.path.join(output_folder, "info", "training_info_{0}_{1}_epochs.pkl".format(str(epoch+1), str(cam)))
        with open(training_info_path, "wb") as f:
            pkl.dump(training_info, f, protocol=pkl.HIGHEST_PROTOCOL)

    print("Training has finished after {0} epochs\nThe weights have been stored in {1}".format(epoch,model_path))

if __name__ == '__main__':
    epochs = 10
    train(num_epochs=epochs, cam='top') # cam can be ['front','top']
