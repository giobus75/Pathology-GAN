# Starting from NVIDIA PyTorch NGC Container
# https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch
FROM nvcr.io/nvidia/tensorflow:20.03-tf1-py3

# install some useful tools
RUN \
    export DEBIAN_FRONTEND=noninteractive \
    && apt-get update -y -q \
    && apt-get install -y \
    aptitude \
    automake \
    bash-completion \
    build-essential \
    cmake \
    fish \
    git \
    htop \
    less \
    libtool \
    libopencv-dev \
    mc \
    ssh \
    sudo \
    tmux \
    vim \
    wget \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8888
########################################################################
# Install plugin and run as user
########################################################################
RUN \
    useradd -m -G sudo -s /usr/bin/fish -p '*' user \
    && sed -i 's/ALL$/NOPASSWD:ALL/' /etc/sudoers 

COPY ./requirements.txt /home/user/
#RUN chown -R user.user '/home/user/PathologyGAN'

WORKDIR /home/user/
RUN pip3 install -r requirements.txt
#RUN pip3 install --upgrade jupyter lab
USER user
