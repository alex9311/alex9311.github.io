---
layout: post
title:  "Pose Estimation"
date:   2020-01-02
categories: machine learning docker pose estimation
---

I've had some exposure to pose estimation at work and had been wanting to try it out on my own.
My goal for this bloag was to try a state-of-the-art pose estimation on a video and use the data for some insight.
More specifically, I wanted to use pose estimation to analyze form on the rowing machine.

## Find a Model
Human pose estimation is a well researched topic, so I searched for an existing architecture and pre-trained model I could use.
After some googling, I found the [github repo for a pose estimation from a CVPR 2019 publication](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch).
At the time of writing this post, the paper already had 90 citation and the github has over 2k stars and nearly 500 forks.
Despite the success and popularity of the project, the git repo has a number of issues opened by folks having trouble using the model from the paper in their own projects.
After reviewing the issues and struggling to use the model on my own videos, I identified **three problems** to solve:
1. An easily reproducible inference environment is needed ([cuda-related issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/30), [tensorboard issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/98), [opencv issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/123))
2. A script to infer on a video doesn't exist yet. Further, code is also missing for a person detector, which is required as a preprocessing step to pose estimation for images "from the wild" ([open issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/41), [related issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/9))
3. Access to the detected pose keypoints, rather than just an image with the keypoints drawn on it

### 1: Reproducible Environment
I like to use Docker to manage my programming environments.
The repo I worked with is a Pytorch implementation of the pose estimation model, so Pytorch will need to be installed on the image.
I will also need CUDA and CUDNN to use GPUs, OpenCV and FFmpeg to process video, and several python libraries.

Fortunately, NVIDIA provides a Docker image `nvidia/cuda:10.2-cudnn7-devel-ubuntu16.04` that gets me most of what I need.
Beyond that, building OpenCV and FFmpeg in the Dockerfile is well documented online.

With my Docker image, someone wanting to try out pose estimation would simply need to download the pretrained model weights from the CVPR researchers' site, build the docker image, and run the inference script inside it!

### 2: Adding Inference Script and Person Detection
The repo provides the pose estimation model implementation, pre-trained weights, and API to call the model.
The missing components are:
1. Code to read frames from video
2. Code to detect a person in a frame and put a box around them
3. Code Take the pose estimation output and put it back together in a video

The diagram below shows the full inference process including the missing pieces I added.
The exact code can be found on my github.

![images/pose-estimation-diagram.png](/images/pose-estimation-diagram.png)

The first addition (reading frames from video) was an easy to implement with `opencv-python`.
```python
improt cv2

vidcap = cv2.VideoCapture(args.videoFile)
success, image = vidcap.read()

while success:
    # do things with image!
    success, image = vidcap.read()
```

The second addition was the person detector.
This is where I discovered a [torchvision.models](https://pytorch.org/docs/stable/torchvision/models.html)!
This fantastic Python package lets you download pretrained models with a few lines of code.
I used Faster R-CNN pre-trained on ResNet50 as my person detector.

```python
import torchvision;
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True);
model.eval()
```

Below, you can see how much adding the person detector helps the pose estimation.
The top video is the result of running pose estimation on the full frame.
The bottom video is the result of detecting Stalone and running the pose estimator on a tight crop of just him.

![images/pose-estimation-no-person-detect.gif](/images/pose-estimation-no-person-detect.gif)
![images/pose-estimation-no-person-detect.gif](/images/pose-estimation-rocky.gif)

The third addition was stiching back the frames with pose estimations drawn on them.
Thanks to FFMpeg this was a quick implementation!
```python
# args.inferenceFps is an int for the inference frame rate
# pose_dir is the directory 
os.system("ffmpeg -pattern_type glob -i '"
          + pose_dir
          + "/*.jpg' -c:v libx264 -vf fps="
          + str(args.inferenceFps)+" -pix_fmt yuv420p /output/movie.mp4")
```

### 3: Access to Pose Coordinates
This third step was something I added for my own project.
Having a video with the pose estimation drawn on the frames is great for demos, but it isn't very useful in practice.
I wanted to store the coordinates of each keypoint for each frame for later analysis.

## Apply Pose Estimation to Rowing
Great!
I have an easy-to-use pose estmation setup.
The goal that inspired all this work to begin with was analysing erg technique.

