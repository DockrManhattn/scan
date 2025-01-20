#!/bin/bash

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

if ! command_exists grc; then
    echo "Installing grc..."
    sudo apt update
    sudo apt install -y grc
else
    echo "grc is already installed."
fi

if ! command_exists pipx; then
    echo "Installing pipx..."
    sudo apt install -y python3-pip
    pip install --user pipx
else
    echo "pipx is already installed."
fi

echo "Installing netexec via pipx..."
pipx install netexec
netexec --version

echo "Downloading RustScan..."
wget https://github.com/RustScan/RustScan/releases/download/2.3.0/rustscan_2.3.0_amd64.deb
echo "Installing RustScan..."
sudo apt install ./rustscan_2.3.0_amd64.deb

target_dir="/home/$(whoami)/.local/bin"

# Check if the directory exists, if not, create it
if [ ! -d "$target_dir" ]; then
  mkdir -p "$target_dir"
fi

# Copy the scan.sh file and make it executable
cp ./scan.sh "$target_dir/scan"
chmod +x "$target_dir/scan"
