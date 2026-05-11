def get_pipx_cmd():
    """Return pipx command, checking both PATH and common user install locations."""
    if command_exists("pipx"):
        return "pipx"
    # pip install --user puts it here
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
