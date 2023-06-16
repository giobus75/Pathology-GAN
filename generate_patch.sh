#!/bin/bash

N=$1
rm -rf evaluation/
python3 generate_fake_samples.py --checkpoint ckpt/PathologyGAN.ckt --num_samples ${N} --z_dim 200 --main_path . 
