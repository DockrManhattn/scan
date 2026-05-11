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

def get_nxc_version():
    for cmd in ["nxc", "netexec"]:
        if command_exists(cmd):
            try:
                result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
                version_str = result.stdout.strip().split()[0]
                return tuple(int(x) for x in version_str.split("."))
            except Exception:
                pass
    return None

def fix_nxc_db():
    db_path = os.path.expanduser("~/.nxc/workspaces/default/smb.db")
    if os.path.exists(db_path):
        print("Removing stale nxc SMB DB to fix schema mismatch...")
        os.remove(db_path)
        print("  Done. nxc will reinitialize the DB on next run.")
    else:
        print("No stale nxc SMB DB found, skipping.")

def ensure_system_tools():
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

    nxc_version = get_nxc_version()
    if nxc_version and nxc_version >= (1, 3, 0):
        print(f"netexec (nxc) is already at {'.'.join(str(x) for x in nxc_version)}, skipping.")
    else:
        if nxc_version:
            print(f"netexec version {'.'.join(str(x) for x in nxc_version)} is outdated, upgrading to 1.3+...")
        else:
            print("Installing netexec via pipx...")
        result = subprocess.run(["pipx", "install", "git+https://github.com/Pennyw0rth/NetExec", "--force"])
        if result.returncode != 0:
            print("  WARNING: pipx install netexec failed. Install manually.")

    fix_nxc_db()

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

if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "install":
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
        "colorama",
    ],
    entry_points={
        "console_scripts": [
            "scan=scan:main",
        ],
    },
    python_requires=">=3.8",
)
