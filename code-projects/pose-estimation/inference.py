from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import csv
import os
import shutil

from PIL import Image
import matplotlib.pyplot as plt
import torch
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim
import torch.utils.data
import torch.utils.data.distributed
import torchvision
import torchvision.transforms as transforms
import cv2
import numpy as np

import _init_paths
import models
from config import cfg
from config import update_config
from core.function import get_final_preds
from utils.transforms import get_affine_transform

COCO_KEYPOINT_INDEXES = {
    0: 'nose',
    1: 'left_eye',
    2: 'right_eye',
    3: 'left_ear',
    4: 'right_ear',
    5: 'left_shoulder',
    6: 'right_shoulder',
    7: 'left_elbow',
    8: 'right_elbow',
    9: 'left_wrist',
    10: 'right_wrist',
    11: 'left_hip',
    12: 'right_hip',
    13: 'left_knee',
    14: 'right_knee',
    15: 'left_ankle',
    16: 'right_ankle'
}

COCO_INSTANCE_CATEGORY_NAMES = [
    '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
    'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A',
    'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
    'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
    'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
    'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table',
    'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book',
    'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]


def get_object_detection_prediction(model, img_path, threshold):
    img = Image.open(img_path)  # Load the image
    transform = transforms.Compose([transforms.ToTensor()])  # Defing PyTorch Transform
    img = transform(img)  # Apply the transform to the image
    pred = model([img])  # Pass the image to the model
    pred_class = [COCO_INSTANCE_CATEGORY_NAMES[i]
                  for i in list(pred[0]['labels'].numpy())]  # Get the Prediction Score
    pred_boxes = [[(i[0], i[1]), (i[2], i[3])]
                  for i in list(pred[0]['boxes'].detach().numpy())]  # Bounding boxes
    pred_score = list(pred[0]['scores'].detach().numpy())
    # Get list of index with score greater than threshold.
    pred_t = [pred_score.index(x) for x in pred_score if x > threshold][-1]
    pred_boxes = pred_boxes[:pred_t+1]
    pred_class = pred_class[:pred_t+1]
    return pred_boxes, pred_class


def object_detection_api(model, img_path, threshold=0.5):
    boxes, pred_cls = get_object_detection_prediction(model, img_path, threshold)  # Get predictions
    img = cv2.imread(img_path)  # Read image with cv2
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
    for idx, box in enumerate(boxes):
        if pred_cls[idx] == 'person':
            cv2.rectangle(img, box[0], box[1], color=(0, 255, 0),
                          thickness=3)  # Draw Rectangle with the coordinates
            cv2.putText(img, pred_cls[idx], box[0], cv2.FONT_HERSHEY_SIMPLEX,
                        3, (0, 255, 0), thickness=3)  # Write the prediction class

    plt.figure()  # display the output image
    plt.imshow(img)
    plt.xticks([])
    plt.yticks([])
    return plt, boxes


def parse_args():
    parser = argparse.ArgumentParser(description='Train keypoints network')
    # general
    parser.add_argument('--cfg',  type=str, required=True)
    parser.add_argument('--videoFile', type=str, required=True)
    parser.add_argument('--outputDir', type=str, default='/output/')

    parser.add_argument('opts',
                        help='Modify config options using the command-line',
                        default=None,
                        nargs=argparse.REMAINDER)

    args = parser.parse_args()

    # args expected by supporting codebase
    args.modelDir = ''
    args.logDir = ''
    args.dataDir = ''
    args.prevModelDir = ''
    return args


def _xywh2cs(
        bottom_left_x, bottom_left_y,
        box_width, box_height,
        image_width, image_height):
    center = np.zeros((2), dtype=np.float32)
    center[0] = bottom_left_x + box_width * 0.5
    center[1] = bottom_left_y + box_height * 0.5

    aspect_ratio = image_width * 1.0 / image_height
    pixel_std = 200

    if box_width > aspect_ratio * box_height:
        box_height = box_width * 1.0 / aspect_ratio
    elif box_width < aspect_ratio * box_height:
        box_width = box_height * aspect_ratio
    scale = np.array(
        [box_width * 1.0 / pixel_std, box_height * 1.0 / pixel_std],
        dtype=np.float32)
    if center[0] != -1:
        scale = scale * 1.25

    return center, scale


def prepare_output_dirs(prefix='/output/'):
    frame_dir = prefix+'frames/'
    pose_dir = prefix+'poses/'
    box_dir = prefix+'boxes/'
    if os.path.exists(frame_dir) and os.path.isdir(frame_dir):
        shutil.rmtree(frame_dir)
    if os.path.exists(pose_dir) and os.path.isdir(pose_dir):
        shutil.rmtree(pose_dir)
    if os.path.exists(box_dir) and os.path.isdir(box_dir):
        shutil.rmtree(box_dir)
    os.makedirs(frame_dir, exist_ok=True)
    os.makedirs(pose_dir, exist_ok=True)
    os.makedirs(box_dir, exist_ok=True)
    return frame_dir, pose_dir, box_dir


def main():
    # cudnn related setting
    cudnn.benchmark = cfg.CUDNN.BENCHMARK
    torch.backends.cudnn.deterministic = cfg.CUDNN.DETERMINISTIC
    torch.backends.cudnn.enabled = cfg.CUDNN.ENABLED

    args = parse_args()
    update_config(cfg, args)
    frame_dir, pose_dir, box_dir = prepare_output_dirs(args.outputDir)
    csv_output_filename = args.outputDir+'pose-data.csv'
    csv_output_rows = []

    box_model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
    box_model.eval()

    pose_model = eval('models.'+cfg.MODEL.NAME+'.get_pose_net')(
        cfg, is_train=False
    )

    if cfg.TEST.MODEL_FILE:
        print('=> loading model from {}'.format(cfg.TEST.MODEL_FILE))
        pose_model.load_state_dict(torch.load(cfg.TEST.MODEL_FILE), strict=False)
    else:
        print('expected model defined in config at TEST.MODEL_FILE')

    pose_model = torch.nn.DataParallel(pose_model, device_ids=cfg.GPUS).cuda()

    # Loading an video
    vidcap = cv2.VideoCapture(args.videoFile)
    success, image = vidcap.read()
    count = 0

    while success and count < 11:
        print(count)
        if count % 2 != 0:
            # every other frame
            count += 1
            continue

        count_str = str(count).zfill(32)
        frame_local = frame_dir+'frame%s.jpg' % count_str
        cv2.imwrite(frame_local, image)

        # object detection box
        box_plt, boxes = object_detection_api(box_model, frame_local, threshold=0.8)
        box_plt.savefig(box_dir+'box%s.jpg' % count_str)

        bottom_left_corner = boxes[0][0]
        top_right_corner = boxes[0][1]
        box_width = top_right_corner[0]-bottom_left_corner[0]
        box_height = top_right_corner[1]-bottom_left_corner[1]
        center, scale = _xywh2cs(
            bottom_left_corner[0], bottom_left_corner[1],
            box_width, box_height,
            cfg.MODEL.IMAGE_SIZE[0], cfg.MODEL.IMAGE_SIZE[1])
        rotation = 0

        # pose estimation
        data_numpy = cv2.imread(frame_local, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
        trans = get_affine_transform(center, scale, rotation, cfg.MODEL.IMAGE_SIZE)
        model_input = cv2.warpAffine(
            data_numpy,
            trans,
            (int(cfg.MODEL.IMAGE_SIZE[0]), int(cfg.MODEL.IMAGE_SIZE[1])),
            flags=cv2.INTER_LINEAR)
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        model_input = transform(model_input).unsqueeze(0)
        # switch to evaluate mode
        pose_model.eval()
        with torch.no_grad():
            # compute output heatmap
            output = pose_model(model_input)
            preds, _ = get_final_preds(
                cfg,
                output.clone().cpu().numpy(),
                np.asarray([center]),
                np.asarray([scale]))

            image = data_numpy.copy()
            new_csv_row = [count]
            for idx, mat in enumerate(preds[0]):
                x_coord, y_coord = int(mat[0]), int(mat[1])
                cv2.circle(image, (x_coord, y_coord), 2, (255, 0, 0), 2)
                new_csv_row.extend([x_coord, y_coord])

            csv_output_rows.append(new_csv_row)
            # vis result
            cv2.imwrite(pose_dir+'pose%s.jpg' % count_str, image)

        success, image = vidcap.read()
        count += 1

    csv_headers = ['frame']
    for keypoint in COCO_KEYPOINT_INDEXES.values():
        csv_headers.extend([keypoint+'_x', keypoint+'_y'])

    with open(csv_output_filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(csv_headers)
        csvwriter.writerows(csv_output_rows)


if __name__ == '__main__':
    main()
