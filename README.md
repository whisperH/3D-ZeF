## 3D-ZeF: A 3D Zebrafish Tracking Benchmark Dataset

This repository contains the code and scripts for the paper *3D-ZeF: A 3D Zebrafish Tracking Benchmark Dataset*

The paper investigates tracking multiple zebrafish simuntaniously from two unique camea views, in order to generate 3D trajectories of each zebrafish.
In the paper we present our novel zebrafish 3D tracking dataset, recorded in a laboratory environment at Aalborg, Denmark. The data is publicly available at our [MOT Challenge page](https://motchallenge.net/data/3D-ZeF20).


As this is a collection of research code, one might find some occasional rough edges. We have tried to clean up the code to a decent level but if you encounter a bug or a regular mistake, please report it in our issue tracker. 
### Zbrafish 毒理实验
- 1.相机标定 运行video2img.py，将标定的视频文件转化成图片，然后使用matlab双目标定，计算内外参矩阵

- 2.运行 ```common/ImgPosition.py```文件
  -  标定时间、水箱位置
        ```bash
        python common/ImgPosition.py --view top --path D:\\program\\PotPlayer\\Capture
        python common/ImgPosition.py --view left --path D:\\program\\PotPlayer\\Capture
        python common/ImgPosition.py --view right --path D:\\program\\PotPlayer\\Capture
        ```

  -  根据标定结果，配置```E:\data\3D_pre\0918-0919fish```下setting.ini文件
        ```bash
        [ExpArea]字段中
        exp_list = 1_1, 2_CK, 3_1, 4_1
        
        cam_list = D01,D02,D04
        
        D01_time_pos = 1192,27,1676,78
        D02_time_pos = 1193,26,1681,76
        D04_time_pos = 1200,58,1687,109
        
        D01_area = 1_1, 581, 93, 1020, 524 # {box_np}_{potency}, tl_x, tl_y, br_x, br_y
            2_CK, 1050, 79, 1514, 535
            3_1, 547, 556, 1010, 1047
            4_1, 1049, 562, 1491, 1037
        D04_area = 1_1, 98, 594, 974, 1007
            3_1, 994, 598, 1890, 1000
        D02_area = 4_1, 196, 593, 971, 978
            2_CK, 993, 616, 1792, 965
        ```
- 3.切割视频:```python modules/dataset_processing/cutTank.py```文件，多线程执行文件
    - 切割时间设定 {视频文件夹} 下的settings.ini文件，多个时间点以空行分开，注意不要加空格。
        ```bash
        D01_20210918195000.mp4=2021_09_18_19_51_20(strat time)
            2021_09_18_19_55_20(strat time)
        ```
        ```python threading_cutRegion.py```标定时间、水箱位置，注意要修改 exp_floder的根目录位置
        对应每个tank的路径，会在 **视频文件夹/cut_video** 生成切割好的数据，命名规则：```start_time_camNO```
        例如：2021_09_18_19_51_20_D01.avi

- 4.对每段视频执行目标检测 多进程：```python threading_detect.py```
    - 顶部视图使用fastercnn，侧视图使用yolov5，检测生成的结果存储在 **视频文件夹/processed/{region_name}** 中。
    
- 5.在目标检测的基础上执行 ```BgDetector.py``` 多进程：```python threading_bgdetect.py```
    - 首先将根目录下的settings.ini文件复制到 cut_video文件中，执行传统CV的特征提取方法，计算出一系列指标后存储于bg_processed
    文件夹下（按隔间存储）

### Zebrafish Tracker Overview
#### Tracker Pipeline 
Use the "pipeline-env.yml" Anaconda environment and run the provided Pipeline bat scripts for running the entire tracking pipeline at a given directory path. The directory path should contain:
 
 * cam1.mp4 and cam2.mp4, of the top and front views respectively, or the image folders ImgF and ImgT.
 * cam1_references.json and cam2_references.json, containing the world <-> camera correspondance, and the cam1_intrinsic.json and cam2_intrinsic.json files containg the intrinsic camera parameters..
 * cam1.pkl and cam2.pkl containing the camera calibrations.
 * cam1.pkl and cam2.pkl are crated using the JsonToCamera.py script in the reconstruction folder. When using the references and intrinsic json files from the MOTChallenge data folder, you need to rename the camT_\*.json files to cam1_\*.json and camF_\*.json to cam2_\*.json.  
 * settings.ini file such as the provided dummy_settings.ini, with line 2, 13, 14, 41 and 42 adjusted to the specific videos.
 * Have an empty folder called "processed".


##### Script Descriptions

ExtractBackground.py
    
    Creates a median image of the video, used for background subtraction in BgDetector.py

BgDetector.py
    
    Runs thorugh the specified camera view and detects bounding boxes and keypoint for the zebrafish in all of the frames of the video. Can also provide previously detected bounding boxes, in which case they are processed for the next step.

TrackerVisual.py
    
    Runs through the specified camera view and construct initial 2D tracklets from the detected keypoints.
    
TrackletMatching.py

    Goes through the 2D tracklets from TrackerVisual.py and tries to make them into 3D tracklets.
    
    Pull the newest commit from our repo, which contains an updated Camera.py script and the new JsonToCamera.py script (https://bitbucket.org/aauvap/3d-zef/src/master/modules/reconstruction/JsonToCamera.py)
    You should rename the intrinsic and references json files from the MOTChallenge data folder as follows:
    
    
    camT_references.json -> cam1_references.json
    camF_references.json -> cam2_references.json
    
    
    camT_intrinsic.json -> cam1_intrinsic.json
    camF_intrinsic.json -> cam2_intrinsic.json
    
    
    you should then run the following commands from the reconstruction folder:
    
    python JsonToCamera.py -f (PathToJsonFIles) -c 1
    python JsonToCamera.py -f (PathToJsonFIles) -c 2
    
    You should then be able to run the TrackletMatching and FinalizeTracklets scripts :)
    
FinalizeTracks.py
    
    Goes through the 3D tracklets from TrackeltMatching.py, and combiens them into full 3D tracks



#### Faster RCNN
To train and evaluate using the Faster RCNN method, go to the folder "modules/fasterrcnn".
Utilize the provided docker file. if there are any problems read the DOCKER_README.md file.
The Faster RCNN Code is based on the torchvision object detection fine tuning guide: https://pytorch.org/tutorials/intermediate/torchvision_tutorial.html

##### Pretrained models

The utilized pretrained Faster RCNN models are available at this [Dropbox link](https://www.dropbox.com/s/fesalzi16usruso/3DZeF_pretrained_fasterrcnn.zip?dl=0)

##### Script Descriptions

train.py
    
    Trains a Faster RCNN with a ResNet50 FPN bakbone. Expects the data to be in a subfolder called "data" and with the child folders "train" and "valid". In each of these folders all the extracted images and a file called "annotations.csv" should be placed. The annotations should be in the AAU VAP Bounding Box annotation format.

evaluateVideo.py
    
    Runs the Faster RCNN on a provided video with the provided model weights. The output is placed in the provided output dir.

evaluateImages.py
    
    Runs the Faster RCNN on a provided images with the provided model weights. The output is placed in the provided output dir.


#### MOT METRICS
In order to obtain the MOT metrics of the complete tracking output, the MOTMetrics.bat script should be run. For this task the Anaconda environment described in "motmetrics-enc.yml" should be used.
This requires that at the provided directory path, there is a folder called "gt" with a "annotations_full.csv" file or the gt.txt file from the MOT Challenge page, and an empty folder called "metrics". When using gt.txt the --useMOTFormat should be supplied.
The metrics are calculated using the py-motmetrics package: https://github.com/cheind/py-motmetrics (Version used: 1.1.3.  Retrieved: 30th August 2019)



### License

All code is licensed under the MIT license, except for the pymotmetrics and torchvision code reference, which are subject to their respective licenses when applicable.



### Acknowledgements
Please cite the following paper if you use our code or dataset:

```TeX
@InProceedings{Pedersen_2020_CVPR,
author = {Pedersen, Malte and Haurum, Joakim Bruslund and Bengtson, Stefan Hein and Moeslund, Thomas B.},
title = {3D-ZeF: A 3D Zebrafish Tracking Benchmark Dataset},
booktitle = {IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
month = {June},
year = {2020}
}
```