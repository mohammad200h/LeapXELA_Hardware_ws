# install Eigen 3.3.9.

# install dq-robotics

# install dep
 apt-get install -y build-essential cmake git libpoco-dev  libfmt-dev

# build libfranka 0.9.2

git clone https://github.com/frankaemika/libfranka.git
cd libfranka
git checkout 0.9.2 
git submodule init 
git submodule update 


mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DCMAKE_INSTALL_PREFIX=/home/user/Libraries/libfranka ..
cmake --build .
cmake --install .



