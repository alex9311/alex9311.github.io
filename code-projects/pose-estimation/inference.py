from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import csv
import os
import shutil

from PIL import Image
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

from common import COCO_KEYPOINT_INDEXES
from common import COCO_INSTANCE_CATEGORY_NAMES
from common import get_person_detection_boxes
from common import get_pose_estimation_prediction
from common import box_to_center_scale


def prepare_output_dirs(prefix='/output/'):
    pose_dir = prefix+'poses/'
    box_dir = prefix+'boxes/'
    if os.path.exists(pose_dir) and os.path.isdir(pose_dir):
        shutil.rmtree(pose_dir)
    if os.path.exists(box_dir) and os.path.isdir(box_dir):
        shutil.rmtree(box_dir)
    os.makedirs(pose_dir, exist_ok=True)
    os.makedirs(box_dir, exist_ok=True)
    return pose_dir, box_dir


def parse_args():
    parser = argparse.ArgumentParser(description='Train keypoints network')
    # general
    parser.add_argument('--cfg',  type=str, required=True)
    parser.add_argument('--videoFile', type=str, required=True)
    parser.add_argument('--outputDir', type=str, default='/output/')
    parser.add_argument('--inferenceFps', type=int, default=10)
    parser.add_argument('--writeBoxFrames', action='store_true')

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


def main():
    # cudnn related setting
    cudnn.benchmark = cfg.CUDNN.BENCHMARK
    torch.backends.cudnn.deterministic = cfg.CUDNN.DETERMINISTIC
    torch.backends.cudnn.enabled = cfg.CUDNN.ENABLED

    args = parse_args()
    update_config(cfg, args)
    pose_dir, box_dir = prepare_output_dirs(args.outputDir)
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
    fps = vidcap.get(cv2.CAP_PROP_FPS)
    if fps < args.inferenceFps:
        print('desired inference fps is '+str(args.inferenceFps)+' but video fps is '+str(fps))
        exit()
    every_nth_frame = round(fps/args.inferenceFps)

    success, image_bgr = vidcap.read()
    count = 0

    while success:
        if count % every_nth_frame != 0:
            count += 1
            continue

        image = image_bgr[:, :, [2, 1, 0]]
        count_str = str(count).zfill(32)

        # object detection box
        pred_boxes = get_person_detection_boxes(box_model, image, threshold=0.8)
        if args.writeBoxFrames:
            image_bgr_box = image_bgr.copy()
            for box in pred_boxes:
                cv2.rectangle(image_bgr_box, box[0], box[1], color=(0, 255, 0),
                              thickness=3)  # Draw Rectangle with the coordinates
            cv2.imwrite(box_dir+'box%s.jpg' % count_str, image_bgr_box)

        # pose estimation
        box = pred_boxes[0]  # assume there is only 1 person
        center, scale = box_to_center_scale(box, cfg.MODEL.IMAGE_SIZE[0], cfg.MODEL.IMAGE_SIZE[1])
        pose_preds = get_pose_estimation_prediction(pose_model, image, center, scale)

        new_csv_row = []
        for idx, mat in enumerate(pose_preds[0]):
            x_coord, y_coord = int(mat[0]), int(mat[1])
            cv2.circle(image_bgr, (x_coord, y_coord), 4, (255, 0, 0), 2)
            new_csv_row.extend([x_coord, y_coord])

        csv_output_rows.append(new_csv_row)
        cv2.imwrite(pose_dir+'pose%s.jpg' % count_str, image_bgr)

        # get next frame
        success, image_bgr = vidcap.read()
        count += 1

    # write csv
    csv_headers = ['frame']
    for keypoint in COCO_KEYPOINT_INDEXES.values():
        csv_headers.extend([keypoint+'_x', keypoint+'_y'])

    with open(csv_output_filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(csv_headers)
        csvwriter.writerows(csv_output_rows)

    pose_dir = '/output/poses/'
    os.system("ffmpeg -y -pattern_type glob -i '"
              + pose_dir
              + "/*.jpg' -c:v libx264 -vf fps="
              + str(args.inferenceFps)+" -pix_fmt yuv420p /output/movie.mp4")


if __name__ == '__main__':
    main()
