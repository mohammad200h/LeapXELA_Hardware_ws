# FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04
FROM ubuntu:22.04

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository universe

RUN apt-get update && apt-get install -y git
RUN apt-get update && apt install -y mesa-utils

# Install EGL libraries for headless MuJoCo rendering
RUN apt-get update && apt-get install -y libegl1-mesa libgl1-mesa-glx libglib2.0-0
RUN apt-get update && apt install -y libfuse2

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

#colcon build
RUN  apt update && apt install -y python3-colcon-common-extensions

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

##### Terminator ####
RUN apt-get update && apt-get install -y terminator

###### WorkDir #######
WORKDIR workspace

###### Shell #######
CMD /bin/bash
