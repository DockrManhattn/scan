import os
import shutil
import subprocess
import sys
from setuptools import setup


def command_exists(name):
    return shutil.which(name) is not None


def apt_install(package):
    result = subprocess.run(["sudo", "apt", "install", "-y", package])
    if result.returncode != 0:
        print(f"  WARNING: apt install {package} failed (exit {result.returncode}). Install manually.")


def ensure_system_tools():
    grc_path = shutil.which("grc")
    home = os.path.expanduser("~")
    if grc_path and not grc_path.startswith(home):
        print("grc is already installed.")
    else:
        print("Installing grc...")
        result = subprocess.run(["sudo", "apt", "install", "-y", "grc"])
        if result.returncode != 0:
            print("  WARNING: apt install grc failed. grc is optional; nmap will run without it.")

    if command_exists("pipx"):
        print("pipx is already installed.")
    else:
        print("Installing pipx...")
        apt_install("python3-pip")
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "pipx"])

    if command_exists("nmap"):
        print("nmap is already installed.")
    else:
        print("Installing nmap...")
        apt_install("nmap")

    if command_exists("nxc") or command_exists("netexec"):
        print("netexec (nxc) is already installed.")
    else:
        print("Installing netexec via pipx...")
        result = subprocess.run(["pipx", "install", "netexec"])
        if result.returncode != 0:
            print("  WARNING: pipx install netexec failed. Install manually.")

    if command_exists("rustscan"):
        print("rustscan is already installed.")
    else:
        print("Downloading RustScan...")
        deb = "rustscan_2.3.0_amd64.deb"
        result = subprocess.run(
            ["wget", "-q", f"https://github.com/RustScan/RustScan/releases/download/2.3.0/{deb}"]
        )
        if result.returncode != 0:
            print("  WARNING: wget failed. Install rustscan manually from github.com/RustScan/RustScan")
        else:
            print("Installing RustScan...")
            subprocess.run(["sudo", "apt", "install", "-y", f"./{deb}"])
            subprocess.run(["rm", "-f", deb])


if __name__ == "__main__" and len(sys.argv) == 1:
    ensure_system_tools()
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "."])
    sys.exit(0)

setup(
    name="scan",
    version="2.0.0",
    description="Network scan helper with rustscan/nmap/nxc, logging, and HTML output",
    author="dockrmanhattn@gmail.com",
    py_modules=["scan"],
    install_requires=[
        "ansi2html",
    ],
    entry_points={
        "console_scripts": [
            "scan=scan:main",
        ],
    },
    python_requires=">=3.8",
)
