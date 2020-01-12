from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import math
import os
import shutil
import statistics

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


def get_speed_from_coords(coords_list):
    print('coords_list:')
    print(coords_list)
    if len(coords_list) <= 1:
        return 0

    i = 1
    distances = []
    while i < len(coords_list):
        x1 = coords_list[i-1][0]
        y1 = coords_list[i-1][1]
        x2 = coords_list[i][0]
        y2 = coords_list[i][1]
        distances.append(math.sqrt((x2 - x1)**2 + (y2 - y1)**2))
        i += 1

    return sum(distances)/len(coords_list)


def get_speed_list(coords_list, point_window=5):
    speed_list = []
    for idx, _ in enumerate(coords_list):
        end_window = idx + 1
        start_window = idx - point_window
        if start_window < 0:
            start_window = 0
        speed_list.append(get_speed_from_coords(coords_list[start_window:end_window]))
    return speed_list


def medianify_coords(coords_list):
    x_values = [x for x, y in coords_list]
    y_values = [y for x, y in coords_list]
    return [statistics.median(x_values), statistics.median(y_values)]


def get_medianified_list(coords_list, point_window=5):
    new_coords_list = coords_list
    look_back_number = point_window//2
    look_forward_number = point_window-1-look_back_number
    current_index = look_back_number+1

    while current_index < len(coords_list)-look_forward_number:
        start_look_back = current_index-look_back_number
        end_look_forward = current_index+look_forward_number+1
        new_coords = medianify_coords(coords_list[start_look_back:end_look_forward])
        new_coords_list[current_index] = new_coords
        current_index += 1

    return new_coords_list


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

    left_wrist_index = [k for k, v in COCO_KEYPOINT_INDEXES.items() if v == 'left_wrist'][0]
    right_wrist_index = [k for k, v in COCO_KEYPOINT_INDEXES.items() if v == 'right_wrist'][0]

    images = []
    left_wrist_coords = []
    right_wrist_coords = []

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

        # opencv reads images from video as BGR, swap to RBG for inferece
        image = image_bgr[:, :, [2, 1, 0]]
        count_str = str(count).zfill(32)

        # object detection box
        pred_boxes = get_person_detection_boxes(box_model, image, threshold=0.8)
        if args.writeBoxFrames:
            for box in pred_boxes:
                cv2.rectangle(image_bgr, box[0], box[1], color=(0, 255, 0),
                              thickness=3)  # Draw Rectangle with the coordinates
            cv2.imwrite(box_dir+'box%s.jpg' % count_str, image_bgr)

        # pose estimation
        box = pred_boxes[0]  # assume there is only 1 person
        center, scale = box_to_center_scale(box, cfg.MODEL.IMAGE_SIZE[0], cfg.MODEL.IMAGE_SIZE[1])
        pose_preds = get_pose_estimation_prediction(pose_model, image, center, scale)

        for idx, mat in enumerate(pose_preds[0]):
            x_coord, y_coord = int(mat[0]), int(mat[1])
            if idx == left_wrist_index:
                left_wrist_coords.append([x_coord, y_coord])
            if idx == right_wrist_index:
                right_wrist_coords.append([x_coord, y_coord])
        images.append(image)

        # get next frame
        success, image_bgr = vidcap.read()
        count += 1

    if True:
        file = open('/output/images.pkl', 'wb')
        pickle.dump({'left_wrist_coords': left_wrist_coords,
                     'right_wrist_coords': right_wrist_coords, 'images': images}, file)
        file.close()

    else:
        file = open('/output/images.pkl', 'rb')
        data = pickle.load(file)
        images = data['images']
        left_wrist_coords = data['left_wrist_coords']
        right_wrist_coords = data['right_wrist_coords']

        file.close()

    smooth_left_wrist = get_medianified_list(left_wrist_coords[:])
    smooth_right_wrist = get_medianified_list(right_wrist_coords[:])

    left_speed_list = get_speed_list(smooth_left_wrist)
    right_speed_list = get_speed_list(smooth_right_wrist)
    hand_speeds = [left_speed_list, right_speed_list]
    average_hand_speeds = [(x+y)/2 for x, y in zip(*hand_speeds)]
    image_height, image_width, _ = images[0].shape
    speed_max = max(average_hand_speeds)
    full_bar_width = round(image_width/2)
    bar_height = round(image_height/10)

    for idx, img_rbg in enumerate(images):
        img_bgr = cv2.cvtColor(img_rbg, cv2.COLOR_RGB2BGR)
        raw_left_coord = (left_wrist_coords[idx][0], left_wrist_coords[idx][1])
        raw_right_coord = (right_wrist_coords[idx][0], right_wrist_coords[idx][1])

        smooth_left_coord = (int(round(smooth_left_wrist[idx][0])), int(
            round(smooth_left_wrist[idx][1])))
        smooth_right_coord = (int(round(smooth_right_wrist[idx][0])), int(
            round(smooth_right_wrist[idx][1])))

        cv2.circle(img_bgr, smooth_left_coord, 4, (0, 255, 0), 2)
        cv2.circle(img_bgr, smooth_right_coord, 4, (0, 255, 0), 2)
        idx_str = str(idx).zfill(32)

        bar_width = round((round(average_hand_speeds[idx])/speed_max)*full_bar_width)
        img_bgr = cv2.rectangle(img_bgr, (0, 0), (full_bar_width, bar_height), (0, 0, 0), -1)
        img_bgr = cv2.rectangle(img_bgr, (0, 0), (bar_width, bar_height), (0, 100, 0), -1)
        cv2.putText(img_bgr, str(round(average_hand_speeds[idx], 3)), (full_bar_width, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 0, 0), 2, cv2.LINE_AA)

        cv2.imwrite(pose_dir+'pose%s.jpg' % str(idx_str), img_bgr)

    pose_dir = '/output/poses/'
    os.system("ffmpeg -y -pattern_type glob -i '"
              + pose_dir
              + "/*.jpg' -c:v libx264 -vf fps="
              + str(args.inferenceFps)+" -pix_fmt yuv420p /output/movie.mp4")


if __name__ == '__main__':
    main()
