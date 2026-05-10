import shutil
import subprocess
import sys
from setuptools import setup
from setuptools.command.install import install


def command_exists(name):
    return shutil.which(name) is not None


def run(cmd, check=True):
    print(f"  Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=check)


def ensure_system_tools():
    if command_exists("grc"):
        print("grc is already installed.")
    else:
        print("Installing grc...")
        run(["sudo", "apt", "install", "-y", "grc"])

    if command_exists("pipx"):
        print("pipx is already installed.")
    else:
        print("Installing pipx...")
        run(["sudo", "apt", "install", "-y", "python3-pip"])
        run([sys.executable, "-m", "pip", "install", "--user", "pipx"])

    if command_exists("nmap"):
        print("nmap is already installed.")
    else:
        print("Installing nmap...")
        run(["sudo", "apt", "install", "-y", "nmap"])

    if command_exists("nxc") or command_exists("netexec"):
        print("netexec (nxc) is already installed.")
    else:
        print("Installing netexec via pipx...")
        run(["pipx", "install", "netexec"])


class InstallWithSystemTools(install):
    def run(self):
        ensure_system_tools()
        super().run()


# Note: rustscan must be installed manually from github.com/RustScan/RustScan

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
    cmdclass={
        "install": InstallWithSystemTools,
    },
)
