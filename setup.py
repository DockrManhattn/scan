from setuptools import setup

# System tool dependencies (not pip-installable, must be installed separately):
#   rustscan  - apt install or .deb from github.com/RustScan/RustScan
#   nmap      - apt install nmap
#   grc       - apt install grc
#   nxc       - pipx install netexec

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
