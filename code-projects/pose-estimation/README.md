## Dockerizing Pose estimation

This code works off an existing [pose estimation repo](https://github.com/leoxiaobin/deep-high-resolution-net.pytorch), but has major additions for ease of use for inference on video with a pretrained model.

### Prep
1. Download pretrained pose estimator from [google drive](https://drive.google.com/drive/folders/1hOTihvbyIxsm5ygDpbUuJ7O_tzv4oXjC?usp=sharing) to this directory under `models/`
2. Put the video file you'd like to infer on in this directory under `videos`
3. build the docker container in this directory with `./build-docker.sh`
4. update the `inference-config.yaml` file to reflect the number of GPUs you have available

### Running the Model
Start your docker container with:
```
nvidia-docker run --rm -it \
  -v $(pwd)/output:/output \
  -v $(pwd)/videos:/videos \
  -v $(pwd)/models:/models \
  -w /pose_root \
  pose_estimator \
  /bin/bash
```
Once the container is running, you can run inference with:
```
python tools/inference.py \
  --cfg inference-config.yaml \
  --videoFile videos/rocky.mp4 \
  --inferenceFps 1 \
  TEST.MODEL_FILE \
  models/pytorch/pose_coco/pose_hrnet_w32_384x288.pth
```
