---
layout: post
title:  "Pose Estimation"
date:   2020-01-02
categories: machine learning docker pose estimation
---

I've had some exposure to pose estimation at work and have been wanting to try it out on my own.
My goal was to try a state-of-the-art pose estimation on a video and use the data for some insight.
More specifically, I'd like to use pose estimation to analyze form during exercise.

## Introduction
After some googling, I found the github repo for a Pose Estimation from a CVPR 2019 publication.
At the time of writing this post, the paper already had 90 citation and the github has over 2k stars and nearly 500 forks.
Despite the apparent success and popularity of the project, the git repo has a number of issues opened by folks having trouble using the model from the paper in their own projects.
After reviewing the issues and struggling to use the model on my own videos, I identified **three problems** to solve:
1. A consistent inference environment is needed ([cuda-related issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/30), [tensorboard issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/98), [opencv issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/123), etc)
2. The pose estimation model requires people to be cropped out of background before pose estimation is run for optimal performance ([open issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/41), [long related issue](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch/issues/9))
3. Access to the detected pose keypoints, rather than just an image with the keypoints drawn on it (this one is for me)

## 1: Consistent Environment
I like to use Docker to manage my programming environments.
The repo I'm working with is a Pytorch implementation of the pose estimation model.
I will also need CUDA, CUDNN, OpenCV to read images/videos, FFmpeg to process video, and several python libraries.

Fortunately, NVIDIA provides a Docker image `nvidia/cuda:10.2-cudnn7-devel-ubuntu16.04` that gets me most of what I need.
Beyond that, building OpenCV and FFmpeg in the Dockerfile is well documented online.

With my Docker image, someone wanting to try out pose estimation would simply need to download the pretrained model, build the docker image, and run the inference script inside it!

## 2: Adding Person Detection
Before working to include add a person detector the inference code, I wanted to confirm that the model failed without it.
The video below is the result of running pose estimator without any person detectiom (automatic or manual).
It isn't pretty!

![images/pose-estimation-no-person-detect.gif](/images/pose-estimation-no-person-detect.gif)

Here is where I discovered a [torchvision.models](https://pytorch.org/docs/stable/torchvision/models.html)!
This fantastic Python package lets you download pretrained models with a few lines of code.
I used Faster R-CNN pre-trained on ResNet50 as my person detector.

```
import torchvision;
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True);
model.eval()
```

![images/pose-estimation-no-person-detect.gif](/images/pose-estimation-rocky.gif)

## 3: Access to Pose Coordinates

