
sudo xhost +local:root



sudo docker run --runtime=nvidia -it --name leap_xela_hardware \
  -v $(pwd)/../../LeapXELA_Hardware_ws:/workspace/LeapXELA_Hardware_ws \
  -v /etc/xela:/etc/xela \
  -v /dev/bus/usb:/dev/bus/usb \
  -v /dev:/dev \
  -v /run/udev:/run/udev:ro \
  -v /dev/video0:/dev/video0 \
  -v /dev/video1:/dev/video1 \
  -v /dev/video2:/dev/video2 \
  -v /dev/video3:/dev/video3 \
  -v /dev/video4:/dev/video4 \
  -v /dev/video5:/dev/video5 \
  -v /dev/video6:/dev/video6 \
  -v /dev/video7:/dev/video7 \
  -v /dev/video8:/dev/video8 \
  -v /dev/video9:/dev/video9 \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  -e DISPLAY -e LOCAL_USER_ID=$(id -u) -e LOCAL_GID=$(id -g) \
  -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -e MUJOCO_GL=egl \
  --net=host  --privileged leap_xela_hardware
