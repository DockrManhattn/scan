import os
import shutil
import subprocess
import sys
import tempfile

def ensure_setuptools():
    """Fix hollow/stub setuptools installs (common on Ubuntu 22.04+)."""
    try:
        import setuptools
        if setuptools.__file__ is None:
            raise ImportError("stub")
        from setuptools import setup  # noqa: F401
        print("setuptools is healthy, skipping reinstall.")
    except (ImportError, AttributeError):
        print("setuptools is missing or broken, reinstalling...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--break-system-packages", "--force-reinstall", "setuptools"
        ])
        if result.returncode != 0:
            print("  pip install failed, trying apt...")
            subprocess.run(["sudo", "apt", "install", "-y", "python3-setuptools"])
        print("Restarting setup with working setuptools...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

ensure_setuptools()

from setuptools import setup  # noqa: E402


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


def get_pipx_cmd():
    """Return pipx command, checking both PATH and common user install locations."""
    if command_exists("pipx"):
        return "pipx"
    user_pipx = os.path.expanduser("~/.local/bin/pipx")
    if os.path.exists(user_pipx):
        return user_pipx
    return None


def ensure_system_tools():
    if command_exists("pipx"):
        print("pipx is already installed.")
    else:
        print("Installing pipx...")
        apt_install("python3-pip")
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "pipx",
                        "--break-system-packages"])

    pipx = get_pipx_cmd()
    if pipx is None:
        print("  ERROR: pipx not found even after install. Add ~/.local/bin to your PATH and re-run.")
        sys.exit(1)

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
        result = subprocess.run([pipx, "install", "git+https://github.com/Pennyw0rth/NetExec", "--force"])
        if result.returncode != 0:
            print("  WARNING: pipx install netexec failed. Install manually.")

    fix_nxc_db()

    if command_exists("rustscan"):
        print("rustscan is already installed.")
    else:
        print("Downloading RustScan...")
        deb = "rustscan_2.3.0_amd64.deb"
        with tempfile.TemporaryDirectory() as tmpdir:
            deb_path = os.path.join(tmpdir, deb)
            result = subprocess.run(
                ["wget", "-q", "-O", deb_path, f"https://github.com/RustScan/RustScan/releases/download/2.3.0/{deb}"]
            )
            if result.returncode != 0:
                print("  WARNING: wget failed. Install rustscan manually from github.com/RustScan/RustScan")
            else:
                print("Installing RustScan...")
                subprocess.run(["sudo", "apt", "install", "-y", deb_path])


def install_scan_script():
    """Copy scan.py to ~/.local/bin/scan.py"""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan.py")
    dst_dir = os.path.expanduser("~/.local/bin")
    dst = os.path.join(dst_dir, "scan.py")

    if not os.path.exists(src):
        print(f"  WARNING: scan.py not found at {src}, skipping copy.")
        return

    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Copied scan.py to {dst}")


def install_alias():
    """Add scan alias to .zshrc or .bashrc depending on current shell."""
    alias_line = 'alias scan="python3 ~/.local/bin/scan.py"'

    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        rc_file = os.path.expanduser("~/.zshrc")
    elif "bash" in shell:
        rc_file = os.path.expanduser("~/.bashrc")
    else:
        print(f"  WARNING: Unknown shell '{shell}', skipping alias install.")
        print(f"  Add this manually to your shell rc file: {alias_line}")
        return

    if os.path.exists(rc_file):
        with open(rc_file, "r") as f:
            if alias_line in f.read():
                print(f"Alias already present in {rc_file}, skipping.")
                return

    with open(rc_file, "a") as f:
        f.write(f"\n# Added by scan installer\n{alias_line}\n")

    print(f"Added alias to {rc_file}")
    print(f"  Run 'source {rc_file}' or open a new terminal to activate it.")


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "install":
        ensure_system_tools()
        install_scan_script()
        install_alias()
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
