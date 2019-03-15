#!/bin/bash

if [ -f lib ]; then
    echo "lib folder already exists! deleting"
    rm -rf lib
fi
mkdir lib
cd lib

# Tweaker3
git clone https://github.com/ChristophSchranz/Tweaker-3/

# Slic3r PE
git clone https://github.com/prusa3d/Slic3r
cd Slic3r
git checkout origin/stable
mkdir build && cd build
cmake .. && make