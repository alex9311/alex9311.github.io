nvidia-docker run --rm -it \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $(pwd)/output:/output \
    -v $(pwd)/videos:/videos \
    -v $(pwd)/models:/pose_root/models \
    -w /pose_root \
	pose_estimator \
	/bin/bash
