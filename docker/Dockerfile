# FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04
FROM nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository universe

RUN apt-get update && apt-get install -y git
RUN apt-get update && apt install -y mesa-utils
# Install EGL libraries for headless MuJoCo rendering
RUN apt-get update && apt-get install -y libegl1-mesa libgl1-mesa-glx libglib2.0-0
RUN apt-get update && apt install -y libfuse2
#
# SAPIEN uses Vulkan for rendering. In containers you often need either:
# - NVIDIA Vulkan ICD from the host (GPU path), or
# - Mesa's lavapipe (CPU Vulkan path) as a fallback.
RUN apt-get update && apt-get install -y \
    libglvnd0 \
    libvulkan1 \
    mesa-vulkan-drivers \
    vulkan-validationlayers \
    && rm -rf /var/lib/apt/lists/*

#### ROS2 Humble ######
ENV ROS_DISTRO=humble

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN apt update && apt install locales
RUN locale-gen en_US en_US.UTF-8
RUN update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
RUN export LANG=en_US.UTF-8

RUN apt install -y software-properties-common
RUN add-apt-repository universe

RUN apt update && apt install curl -y
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg

RUN export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
 && curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    | gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu \
$(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/ros2.list
RUN apt-get update && apt-get install -y ros-${ROS_DISTRO}-desktop

# colcon build + ros2_control (apt-get update must be in the same RUN as install)
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    ros-${ROS_DISTRO}-ros2-control \
    ros-${ROS_DISTRO}-ros2-controllers \
    ros-${ROS_DISTRO}-hardware-interface \
    && rm -rf /var/lib/apt/lists/*

#### Environment setup
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN bash /opt/ros/humble/setup.bash

##### python3.11 ######
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

#### Install dependencies
RUN apt-get install -y python3-pip curl
RUN pip install websocket-client
RUN pip3 install dynamixel-sdk
RUN pip install gradio
RUN pip install h5py
##### Terminator ####
RUN apt-get update && apt-get install -y terminator
##### PyQt5 ######
RUN apt-get update && apt-get install -y libxcb-cursor0
RUN pip install pyqtgraph PySide6

##### realsense ######
# Install RealSense (CUDA-accelerated processing: align, pointcloud, etc.).
# Base image supplies CUDA toolkit; runtime still needs NVIDIA driver + nvidia-container-toolkit (--gpus all).
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
RUN \
    apt-get update && apt-get install -y cmake libssl-dev libusb-1.0-0-dev libudev-dev pkg-config libgtk-3-dev \
    &&                                                             \
    apt-get install -y libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev at \
    &&                                                             \
    git clone https://github.com/IntelRealSense/librealsense.git   \
    &&                                                             \
    cd librealsense                                                \
    &&                                                             \
    git checkout -b development                                    \
    &&                                                             \
    mkdir build && cd build                                        \
    &&                                                             \
    cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_WITH_CUDA=ON \
        -DBUILD_PYTHON_BINDINGS=ON \
        -DPYTHON_EXECUTABLE=/usr/bin/python3 \
    &&                                                             \
    cmake --build .     -j$(nproc)                                 \
    &&                                                             \
    cmake --install .                                              \
    && cd / && rm -rf /librealsense
ENV PYTHONPATH=$PYTHONPATH:/usr/local/lib
##### Dex-retargeting ######
# matplotlib from pip (NumPy 2 ABI). Apt python3-matplotlib targets system NumPy 1.x and breaks when pip installs NumPy 2 (mediapipe imports matplotlib).
RUN python3 -m pip install --no-cache-dir \
    "numpy>=2.0.0" \
    "matplotlib>=3.8.0" \
    "pytransform3d>=3.5.0" \
    "pin>=3.3.1" \
    "nlopt>=2.8.0" \
    "anytree>=2.12.0" \
    "pyyaml>=6.0.0" \
    "lxml>=5.2.2" \
    "tyro" \
    "tqdm" \
    "opencv-python" \
    "mediapipe==0.10.14" \
    "protobuf<5" \
    "sapien==3.0.0b0" \
    "loguru" \
    "torch"

###### Sapian #####
ARG VULKAN_SDK_VERSION=1.4.341.1
RUN cd /tmp && \
    curl -fSL -o "vulkansdk-linux-x86_64-${VULKAN_SDK_VERSION}.tar.xz" \
    "https://sdk.lunarg.com/sdk/download/${VULKAN_SDK_VERSION}/linux/vulkansdk-linux-x86_64-${VULKAN_SDK_VERSION}.tar.xz" && \
    tar -xJf "vulkansdk-linux-x86_64-${VULKAN_SDK_VERSION}.tar.xz" && \
    rm -f "vulkansdk-linux-x86_64-${VULKAN_SDK_VERSION}.tar.xz"
ENV VULKAN_SDK=/tmp/${VULKAN_SDK_VERSION}/x86_64 \
    LD_LIBRARY_PATH=/tmp/${VULKAN_SDK_VERSION}/x86_64/lib \
    VK_LAYER_PATH=/tmp/${VULKAN_SDK_VERSION}/x86_64/etc/vulkan/explicit_layer.d \
    PATH=/tmp/${VULKAN_SDK_VERSION}/x86_64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin


# Vulkan & GLVND Support
RUN apt-get update && apt-get install -y vulkan-tools 
######pybullet ######
RUN pip install pybullet
######onshape-to-robot ######
RUN python3 -m pip install --no-cache-dir "uv>=0.5" "uv-build>=0.5"
RUN cd /tmp && \
    git clone https://github.com/Rhoban/onshape-to-robot.git && \
    cd onshape-to-robot && \
    python3 -m pip install --no-cache-dir --no-build-isolation .
####### Mujoco ######
# MuJoCo 3.2.0
RUN apt-get update && apt-get install -y \
    libglfw3 \
    libglfw3-dev \
    libgl1-mesa-dev \
    libxinerama-dev \
    libxcursor-dev \
    libxrandr-dev \
    libxi-dev \
    ninja-build \
    zlib1g-dev \
    clang-12 \
    && rm -rf /var/lib/apt/lists/*
ARG MUJOCO_VERSION=3.2.0
RUN cd /tmp && \
    git clone -b ${MUJOCO_VERSION} https://github.com/google-deepmind/mujoco.git && \
    cd mujoco && mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local && \
    cmake --build . -j"$(nproc)" && cmake --install . && \
    cd / && rm -rf /tmp/mujoco
RUN pip install mujoco==${MUJOCO_VERSION}
####### perline noise ######
# https://github.com/salaxieb/perlin_noise
RUN pip install perlin-noise
###### open3d ######
RUN pip install open3d
##### Keyboard Control #######
RUN pip install pynput
###### xacro ######
RUN apt-get update && apt-get install -y ros-humble-xacro
##### Joint state publisher ######
RUN apt-get update && apt-get install -y ros-humble-joint-state-publisher-gui
###### nano17 ######
RUN pip install websockets
##### Franka Emika Panda ######
RUN apt-get update && apt-get install -y ros-${ROS_DISTRO}-hardware-interface 
RUN apt-get update && apt-get install -y ros-dev-tools
RUN apt update && apt install -y ros-humble-ament-cmake-clang-format
###### WorkDir #######
WORKDIR /workspace
##### Copy LeapXELA_Hardware_ws ######
COPY . /workspace/LeapXELA_Hardware_ws
WORKDIR /workspace/LeapXELA_Hardware_ws
##### Franka ROS2 dependencies (from multipanda_ros2/tools/Dockerfile) ######
# GCC-11 (required by libfranka)
RUN apt-get update && apt-get install -y gcc-11 g++-11 && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 100 \
    --slave /usr/bin/g++ g++ /usr/bin/g++-11 && \
    rm -rf /var/lib/apt/lists/*

# Eigen 3.3.9
RUN cd /tmp && \
    curl -L https://gitlab.com/libeigen/eigen/-/archive/3.3.9/eigen-3.3.9.tar.gz -o eigen.tar.gz && \
    tar -xzf eigen.tar.gz && cd eigen-3.3.9 && mkdir build && cd build && \
    cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local && \
    cmake --install . && \
    cd / && rm -rf /tmp/eigen.tar.gz /tmp/eigen-3.3.9

# Libfranka 0.9.2
RUN apt-get update && apt-get install -y libpoco-dev && rm -rf /var/lib/apt/lists/*
RUN cd /tmp && \
    git clone https://github.com/frankaemika/libfranka.git && \
    cd libfranka && git checkout 0.9.2 && git submodule update --init --recursive && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DCMAKE_INSTALL_PREFIX=/usr/local .. && \
    cmake --build . -j"$(nproc)" && cmake --install . && \
    cd / && rm -rf /tmp/libfranka

ENV CMAKE_PREFIX_PATH=/usr/local/lib/cmake:${CMAKE_PREFIX_PATH}
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/lib

# dqrobotics
RUN add-apt-repository -y ppa:dqrobotics-dev/release && apt-get update && \
    apt-get install -y libdqrobotics && rm -rf /var/lib/apt/lists/*

# multipanda_ros2 ROS packages (skips packages already installed above)
RUN apt-get update && apt-get install -y \
    build-essential \
    clang-14 \
    clang-format-14 \
    clang-tidy-14 \
    libqt5gui5 \
    libqt5widgets5 \
    libqt5core5a \
    ros-${ROS_DISTRO}-control-msgs \
    ros-${ROS_DISTRO}-ament-clang-format \
    ros-${ROS_DISTRO}-ament-flake8 \
    ros-${ROS_DISTRO}-ament-cmake-clang-tidy \
    ros-${ROS_DISTRO}-angles \
    ros-${ROS_DISTRO}-realtime-tools \
    ros-${ROS_DISTRO}-control-toolbox \
    ros-${ROS_DISTRO}-controller-manager \
    ros-${ROS_DISTRO}-hardware-interface-testing \
    ros-${ROS_DISTRO}-launch-testing \
    ros-${ROS_DISTRO}-generate-parameter-library \
    ros-${ROS_DISTRO}-controller-interface \
    ros-${ROS_DISTRO}-ros2-control-test-assets \
    ros-${ROS_DISTRO}-moveit \
    ros-${ROS_DISTRO}-nav-msgs \
    ros-${ROS_DISTRO}-camera-info-manager \
    ros-${ROS_DISTRO}-joint-state-publisher \
    ros-${ROS_DISTRO}-joint-state-broadcaster \
    ros-${ROS_DISTRO}-robot-state-publisher \
    ros-${ROS_DISTRO}-warehouse-ros-sqlite \
    ros-${ROS_DISTRO}-joint-trajectory-controller \
    ros-${ROS_DISTRO}-rqt \
    ros-${ROS_DISTRO}-rqt-common-plugins \
    ros-${ROS_DISTRO}-rqt-controller-manager \
    ros-${ROS_DISTRO}-rqt-robot-steering \
    ros-${ROS_DISTRO}-rqt-tf-tree \
    ros-${ROS_DISTRO}-rqt-graph \
    ros-${ROS_DISTRO}-rqt-reconfigure \
    ros-${ROS_DISTRO}-rqt-plot \
    ros-${ROS_DISTRO}-teleop-twist-keyboard \
    ros-${ROS_DISTRO}-joy \
    ros-${ROS_DISTRO}-teleop-twist-joy \
    && rm -rf /var/lib/apt/lists/*

RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi
RUN rosdep update

# mujoco_ros_pkgs (tenfoldpaper fork required by multipanda_ros2/franka_hardware; not moveit/mujoco_ros2_control)
RUN apt-get update && apt-get install -y \
    libyaml-cpp-dev \
    libglfw3-dev \
    libfmt-dev \
    && rm -rf /var/lib/apt/lists/*
RUN cd /workspace/LeapXELA_Hardware_ws/ros_ws/src/multipanda_ros2 && \
    rm -rf mujoco_ros_pkgs && \
    git clone -b wip_ros_control_humble --depth 1 https://github.com/tenfoldpaper/mujoco_ros_pkgs.git mujoco_ros_pkgs
ENV MUJOCO_DIR=/usr/local
ENV ROS_VERSION=2
###### Shell #######
CMD /bin/bash
