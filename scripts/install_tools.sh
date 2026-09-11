#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg ninja-build make pkg-config autoconf automake libtool perl
curl --fail --silent --show-error https://apt.llvm.org/llvm-snapshot.gpg.key | gpg --dearmor > /tmp/spark-llvm.gpg
sudo install -m 0644 /tmp/spark-llvm.gpg /usr/share/keyrings/spark-llvm.gpg
echo 'deb [signed-by=/usr/share/keyrings/spark-llvm.gpg] https://apt.llvm.org/noble/ llvm-toolchain-noble-20 main' | sudo tee /etc/apt/sources.list.d/spark-llvm.list
sudo apt-get update
sudo apt-get install -y clang-20 llvm-20 libclang-rt-20-dev libc++-20-dev libc++abi-20-dev
echo /usr/lib/llvm-20/bin >> "$GITHUB_PATH"
python -m pip install 'cmake==3.31.10' 'conan==2.32.0' 'gcovr==8.6'
