#!/usr/bin/env python3
"""
Script Name: scan.py
Description: Template-based script with IP/Port selection and logging.
Author: dockrmanhattn@gmail.com
Date: 2025-11-28
"""

# =========================
# Import Statements
# =========================
import os
import sys
import json
import logging
import argparse
import re
import shutil
import socket
import subprocess
from datetime import datetime
from logging.handlers import RotatingFileHandler
import ipaddress

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    _COLORAMA = True
except ImportError:
    _COLORAMA = False


# =========================
# Default Config (Your Working Version)
# =========================
LOG_LEVEL_DEFAULT = "INFO"
CONFIG_FILENAME = "config.json"
APPLICATION_NAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]
NOTEBOOK_BASEDIR = os.path.expanduser("~/notes/Boxes")
EXCLUDED_PORTS = {0, 1, 38}

SERVICE_PORTS = {
    "ssh": "22",
    "smb": "445",
    "web": "80,443,8000,8080,8081,8082,8443,10000",
    "mysql": "3306",
    "mssql": "1433",
    "winrm": "5985,5986",
    "rdp": "3389",
    "ftp": "21",
    "nfs": "2049",
    "dc": "88",
    "memcached": "11211",
    "smtp": "25",
    "pop3": "110",
    "imap": "143",
    "ldap": "389",
    "ntp": "123",
    "redis": "6379",
    "postgresql": "5432",
    "elasticsearch": "9200,9300",
    "mongodb": "27017",
    "cassandra": "9042",
    "kafka": "9092",
    "rabbitmq": "5672,15672",
    "vnc": "5900",
    "sip": "5060,5061",
    "xmpp": "5222,5269"
}

def _build_discovery_ports():
    ports = set()
    for port_str in SERVICE_PORTS.values():
        for p in port_str.split(","):
            p = p.strip()
            if p:
                ports.add(int(p))
    return ",".join(str(p) for p in sorted(ports))

RUSTSCAN_DISCOVERY_PORTS = _build_discovery_ports()
RUSTSCAN_DISCOVERY_BATCH = 4000
RUSTSCAN_DISCOVERY_FALLBACK_BATCH = 2500
RUSTSCAN_DISCOVERY_ULIMIT = 5000

DEFAULT_CONFIG = {
    "LOG_LEVEL": LOG_LEVEL_DEFAULT,
    "MAX_BYTES": 500_000,            # Approx size for ~1000 lines
    "BACKUP_COUNT": 5,               # Number of rotated logs to keep
    "CURRENT_DIR": os.getcwd(),
    "OUTPUT_DIR": os.path.join(os.getcwd(), APPLICATION_NAME)  # Default; overridden by -o/-outputdir
}

# Static logging style (not persisted to user config)
LOG_STYLE = {
    "BLUE": "\u001b[94m",
    "YELLOW": "\u001b[93m",
    "RED": "\u001b[91m",
    "RESET": "\u001b[0m",
    "DEBUG_EMOJI": "{🔧🐛[+]🐛🔧}",
    "INFO_EMOJI": "{🌀🌵[+]🌵🌀}",
    "WARNING_EMOJI": "{⚡⚡[+]⚡⚡}",
    "ERROR_EMOJI": "{🔥💀[+]💀🔥}",
    "CRITICAL_EMOJI": "{🚨🔥[+]🔥🚨}",
    "DEBUG_PREFIX": "{BLUE}{DEBUG_EMOJI}{RESET}",
    "INFO_PREFIX": "{YELLOW}{INFO_EMOJI}{RESET}",
    "WARNING_PREFIX": "{YELLOW}{WARNING_EMOJI}{RESET}",
    "ERROR_PREFIX": "{RED}{ERROR_EMOJI}{RESET}",
    "CRITICAL_PREFIX": "{RED}{CRITICAL_EMOJI}{RESET}",
}

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
USER_UID = os.getuid()
USER_GID = os.getgid()

# =========================
# Defaults
# =========================
CONFIG_DIR = os.path.expanduser(f"~/.config/{APPLICATION_NAME}")
CONFIG_PATH = os.path.join(CONFIG_DIR, CONFIG_FILENAME)

# =========================
# Apply logging colors/placeholders
# =========================
def apply_color_prefixes(style):
    replacements = {
        "{BLUE}": style["BLUE"],
        "{YELLOW}": style["YELLOW"],
        "{RED}": style["RED"],
        "{RESET}": style["RESET"],
        "{DEBUG_EMOJI}": style["DEBUG_EMOJI"],
        "{INFO_EMOJI}": style["INFO_EMOJI"],
        "{WARNING_EMOJI}": style["WARNING_EMOJI"],
        "{ERROR_EMOJI}": style["ERROR_EMOJI"],
        "{CRITICAL_EMOJI}": style["CRITICAL_EMOJI"],
    }

    def resolve(template: str) -> str:
        for token, value in replacements.items():
            template = template.replace(token, value)
        return template

    style["DEBUG_PREFIX"] = resolve(style["DEBUG_PREFIX"])
    style["INFO_PREFIX"] = resolve(style["INFO_PREFIX"])
    style["WARNING_PREFIX"] = resolve(style["WARNING_PREFIX"])
    style["ERROR_PREFIX"] = resolve(style["ERROR_PREFIX"])
    style["CRITICAL_PREFIX"] = resolve(style["CRITICAL_PREFIX"])

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

# =========================
# Helper: Ensure Config Directory and Write Config
# =========================
def write_config(config_data):
    ensure_config_dir()
    logger = logging.getLogger()
    if logger:
        logger.debug(f"Ensuring config directory: {CONFIG_DIR}")
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    return CONFIG_PATH

# =========================
# Ensure Output Directory
# =========================
def ensure_output_dir(config):
    output_dir = config["OUTPUT_DIR"]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger = logging.getLogger()
        logger.debug(f"Creating output directory: {output_dir}")
    return output_dir

# =========================
# Custom Logging Formatter (Console)
# =========================
class CustomFormatter(logging.Formatter):
    def __init__(self, style):
        super().__init__()
        self.style = style
    def format(self, record):
        if record.levelno == logging.DEBUG:
            prefix = self.style["DEBUG_PREFIX"]
        elif record.levelno == logging.INFO:
            prefix = self.style["INFO_PREFIX"]
        elif record.levelno == logging.WARNING:
            prefix = self.style["WARNING_PREFIX"]
        elif record.levelno == logging.ERROR:
            prefix = self.style["ERROR_PREFIX"]
        elif record.levelno == logging.CRITICAL:
            prefix = self.style["CRITICAL_PREFIX"]
        else:
            prefix = ""
        return f"{prefix} {record.getMessage()}"

# =========================
# Plain Formatter for File Logs
# =========================
class PlainFormatter(logging.Formatter):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    def format(self, record):
        message = self.ansi_escape.sub('', record.getMessage())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] {record.levelname}: {message}"

# =========================
# Setup Logging with Rotation
# =========================
def setup_logging(config, style, cli_log_level=None):
    console_level_str = cli_log_level or config.get("LOG_LEVEL", LOG_LEVEL_DEFAULT)
    console_level = getattr(logging, console_level_str.upper(), logging.INFO)
    logger = logging.getLogger()
    if logger.handlers:
        for h in list(logger.handlers):
            logger.removeHandler(h)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(CustomFormatter(style))
    logger.addHandler(console_handler)
    log_file_path = os.path.join(CONFIG_DIR, f"{APPLICATION_NAME}.log")
    logger.debug(f"Log file will be created at: {log_file_path}")
    file_handler = RotatingFileHandler(
        log_file_path,
        mode="a",
        maxBytes=int(config.get("MAX_BYTES", 500_000)),
        backupCount=int(config.get("BACKUP_COUNT", 5)),
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(PlainFormatter())
    logger.addHandler(file_handler)
    return logger, log_file_path

# =========================
# Tail Log Function
# =========================
def tail_log(log_file_path, lines=200):
    if not os.path.exists(log_file_path):
        print(f"Log file not found: {log_file_path}")
        return
    with open(log_file_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
    for line in all_lines[-lines:]:
        print(line.rstrip())

# =========================
# Handle Log Option
# =========================
def handle_log_option(args, log_file_path):
    if args.log:
        tail_log(log_file_path, lines=200)
        sys.exit(0)

# Logging setup helper
def configure_logging(args, config):
    style = LOG_STYLE.copy()
    apply_color_prefixes(style)
    ensure_config_dir()
    cli_level = "DEBUG" if args.debug else args.log_level
    logger, log_file_path = setup_logging(config, style, cli_log_level=cli_level)
    return logger, log_file_path

# Output directory helper
def prepare_output_dir(args, config, target_identifier):
    work_dir, notes_dir = resolve_output_dir(args, config, target_identifier)
    write_config(config)
    os.makedirs(work_dir, exist_ok=True)
    ensure_output_dir(config)  # ensures notes_dir
    return work_dir, notes_dir

# Target/scan helpers
def resolve_target_ip(target, logger):
    try:
        ipaddress.ip_address(target)
        logger.debug(f"Using provided IP: {target}")
        return target
    except ValueError:
        try:
            resolved = socket.gethostbyname(target)
            logger.info(f"Resolved {target} to {resolved}")
            return resolved
        except socket.gaierror:
            logger.error(f"Could not resolve target: {target}")
            sys.exit(1)

def run_command(cmd, logger, capture=False, check=True, cwd=None, input_text=None):
    logger.debug(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=cwd,
        input=input_text
    )
    if check and result.returncode != 0:
        logger.error(f"Command failed ({result.returncode}): {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result

def ensure_user_ownership(path, logger):
    try:
        os.chown(path, USER_UID, USER_GID)
        logger.debug(f"Set ownership to current user for {path}")
    except PermissionError:
        logger.debug(f"os.chown permission denied for {path}, retrying with sudo.")
        run_command(
            ["sudo", "chown", f"{USER_UID}:{USER_GID}", path],
            logger,
            capture=False,
            check=False
        )
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.debug(f"Chown failed for {path}: {exc}")

def run_rustscan(ip, logger, workdir, attempt=None):
    result = run_command(
        ["rustscan", "-a", ip, "--ulimit", "5000", "--scripts", "none"],
        logger,
        capture=True,
        cwd=workdir
    )
    output = result.stdout or ""
    clean_output = ANSI_ESCAPE.sub("", output)
    ports = sorted({int(p) for p in re.findall(r"Open\s+[0-9\.]+:(\d+)", clean_output)})
    label = f" (attempt {attempt})" if attempt else ""
    logger.debug(f"rustscan raw output{label}:\n{output}")
    if not ports:
        logger.error("No ports found in rustscan output.")
        sys.exit(1)
    logger.debug(f"Open ports {label}: {','.join(map(str, ports))}")
    return ports

def run_rustscan_twice(ip, logger, workdir):
    ports_first = run_rustscan(ip, logger, workdir, attempt=1)
    ports_second = run_rustscan(ip, logger, workdir, attempt=2)
    if ports_first != ports_second:
        logger.debug(
            f"rustscan attempts differed. first={','.join(map(str, ports_first))} "
            f"second={','.join(map(str, ports_second))}"
        )
    combined = sorted(set(ports_first) | set(ports_second))
    if not combined:
        logger.error("No ports found after two rustscan attempts.")
        sys.exit(1)
    logger.info(f"Open ports: {','.join(map(str, combined))}")
    return combined

def filter_ports(ports, excluded):
    return [p for p in ports if p not in excluded]

_PORT_LINE = re.compile(r'^(\d+/\w+)\s+(open|closed|filtered)\s+(\S+)(.*)')
_HEADER_LINE = re.compile(r'^PORT\s+STATE\s+SERVICE')
_REPORT_LINE = re.compile(r'^Nmap scan report|^Host is ')

def _colorize_nmap(text):
    if not _COLORAMA:
        return text
    out = []
    for line in text.splitlines():
        m = _PORT_LINE.match(line)
        if m:
            port, state, service, rest = m.groups()
            if state == "open":
                state_col = Fore.GREEN + Style.BRIGHT + state + Style.RESET_ALL
            elif state == "closed":
                state_col = Fore.RED + state + Style.RESET_ALL
            else:
                state_col = Fore.YELLOW + state + Style.RESET_ALL
            line = (
                Fore.CYAN + Style.BRIGHT + port + Style.RESET_ALL
                + "  " + state_col
                + "  " + Fore.BLUE + service + Style.RESET_ALL
                + rest
            )
        elif _HEADER_LINE.match(line):
            line = Style.BRIGHT + line + Style.RESET_ALL
        elif _REPORT_LINE.match(line):
            line = Fore.YELLOW + Style.BRIGHT + line + Style.RESET_ALL
        out.append(line)
    return "\n".join(out)

def _run_nmap_colorized(cmd, output_file, logger, workdir):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir)
    colorized = _colorize_nmap(result.stdout or "")
    if colorized:
        print(colorized)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(colorized)
    if result.stderr:
        logger.debug(f"nmap stderr: {result.stderr.strip()}")

def run_nmap_udp(ip, workdir, logger):
    output_file = os.path.join(workdir, "001-scan-snmp.md")
    _run_nmap_colorized(
        ["sudo", "nmap", "-sU", "-p", "161", ip],
        output_file, logger, workdir
    )
    if os.path.exists(output_file):
        ensure_user_ownership(output_file, logger)
    return output_file

def run_nmap_tcp(ip, ports, workdir, logger):
    if not ports:
        logger.error("No valid ports to scan with Nmap.")
        sys.exit(1)
    port_str = ",".join(map(str, ports))
    output_file = os.path.join(workdir, "002-scan-nmap.md")
    _run_nmap_colorized(
        ["nmap", "-sCV", "-Pn", "-p", port_str, ip],
        output_file, logger, workdir
    )
    return output_file

def run_nxc_hosts(ip, workdir, logger):
    hosts_file = os.path.join(workdir, "003-hosts-nxc.md")
    run_command(["nxc", "smb", ip, "--generate-hosts-file", hosts_file], logger, cwd=workdir, check=False)
    if os.path.exists(hosts_file):
        ensure_user_ownership(hosts_file, logger)
    if os.path.exists(hosts_file):
        with open(hosts_file, "r", encoding="utf-8") as f:
            content = f.read()
        run_command(["sudo", "tee", "-a", "/etc/hosts"], logger, capture=False, check=False, input_text=content)
    return hosts_file

def log_share_output(logger, label, stdout_text):
    """Log share enumeration results to the console for quick visibility."""
    clean_output = ANSI_ESCAPE.sub("", stdout_text or "").strip()
    if not clean_output:
        logger.info(f"No share output for {label}.")
        return
    logger.info(f"Shares using {label}:")
    for line in clean_output.splitlines():
        logger.info(f"  {line}")

def run_nxc_shares(ip, workdir, logger):
    shares_file = os.path.join(workdir, "004-scan-nxc.md")
    lines = []
    lines.append(f"nxc smb {ip} -u '' -p '' --shares")
    result1 = run_command(["nxc", "smb", ip, "-u", "", "-p", "", "--shares"], logger, capture=True, check=False, cwd=workdir)
    lines.append(result1.stdout or "")
    log_share_output(logger, "null authentication", result1.stdout)
    lines.append("")
    lines.append(f"nxc smb {ip} -u 'a' -p '' --shares")
    result2 = run_command(["nxc", "smb", ip, "-u", "a", "-p", "", "--shares"], logger, capture=True, check=False, cwd=workdir)
    lines.append(result2.stdout or "")
    log_share_output(logger, "guest authentication", result2.stdout)
    with open(shares_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    ensure_user_ownership(shares_file, logger)
    return shares_file

def convert_markdown_to_html(workdir, notes_dir, logger):
    os.makedirs(notes_dir, exist_ok=True)
    for name in os.listdir(workdir):
        if not name.endswith(".md") or not name.startswith("0"):
            continue
        md_path = os.path.join(workdir, name)
        html_path = os.path.join(notes_dir, name + ".html")
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        result = subprocess.run(["ansi2html"], input=md_content, text=True, capture_output=True)
        if result.stdout:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            logger.debug(f"Wrote {html_path}")
        ensure_user_ownership(md_path, logger)
        ensure_user_ownership(html_path, logger)
# =========================
# Parse CLI Arguments
# =========================

def parse_args():
    parser = argparse.ArgumentParser(description="Scan helper with logging and output handling.")
    parser.add_argument("target", nargs="?", help="Target IP or hostname to scan.")
    parser.add_argument("-t", "-target", dest="target_opt", type=str, metavar="",
                        help="Target IP or hostname to scan.")
    parser.add_argument("-log-level", dest="log_level", type=str.upper,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        metavar="", help="Set console logging level")
    parser.add_argument("-debug", action="store_true", help="Enable debug logging (same as -log-level DEBUG)")
    parser.add_argument("-log", action="store_true", help="Show last 200 lines of log and exit.")
    parser.add_argument("-o", "-outputdir", dest="outputdir", type=str, metavar="",
                        help=f"Specify custom base directory (defaults to {NOTEBOOK_BASEDIR}).")
    args = parser.parse_args()
    args.target = args.target or args.target_opt
    if not args.target:
        parser.error("the following arguments are required: target")
    return args

def resolve_output_dir(args, config, target_identifier):
    base_dir = os.path.abspath(os.path.expanduser(os.path.expandvars(args.outputdir))) if args.outputdir else NOTEBOOK_BASEDIR
    cwd = os.getcwd()
    home = os.path.expanduser("~") + os.sep
    if cwd.startswith(home):
        relative = cwd[len(home):]
    else:
        relative = cwd.strip(os.sep)
    if not relative:
        relative = APPLICATION_NAME
    notes_dir = os.path.join(base_dir, relative, target_identifier)

    # Store scan artifacts under a directory named after the target we're scanning
    work_dir = os.path.join(os.getcwd(), target_identifier)
    if os.path.exists(work_dir) and not os.path.isdir(work_dir):
        os.remove(work_dir)

    config["OUTPUT_DIR"] = notes_dir
    return work_dir, notes_dir

def discover_hosts_in_network(network, cidr_str, logger):
    def _run_discovery(batch):
        cmd = [
            "rustscan",
            "-a",
            cidr_str,
            "-b",
            str(batch),
            "-p",
            RUSTSCAN_DISCOVERY_PORTS,
            "--ulimit",
            str(RUSTSCAN_DISCOVERY_ULIMIT),
            "--scripts",
            "none"
        ]
        result = run_command(cmd, logger, capture=True, check=False)
        combined = (result.stdout or "") + (result.stderr or "")
        return result.returncode, ANSI_ESCAPE.sub("", combined), batch

    returncode, output, batch_used = _run_discovery(RUSTSCAN_DISCOVERY_BATCH)
    too_many_files = "Too many open files" in output
    if (returncode != 0 or too_many_files) and RUSTSCAN_DISCOVERY_FALLBACK_BATCH != batch_used:
        logger.warning(
            f"Discovery returned {returncode} with batch {batch_used}"
            f"{' (too many open files detected)' if too_many_files else ''}; "
            f"retrying with batch {RUSTSCAN_DISCOVERY_FALLBACK_BATCH}."
        )
        returncode, output, batch_used = _run_discovery(RUSTSCAN_DISCOVERY_FALLBACK_BATCH)
    ips = set()
    patterns = [
        r"Open\s+(\d{1,3}(?:\.\d{1,3}){3}):\d+",  # Open 192.168.1.10:22
        r"Open\s+\d+/(?:tcp|udp)\s+(\d{1,3}(?:\.\d{1,3}){3})",  # Open 22/tcp 192.168.1.10
        r"(?m)^(\d{1,3}(?:\.\d{1,3}){3})\s*->",  # 192.168.1.10 -> [22]
        r"Open.*?(\d{1,3}(?:\.\d{1,3}){3})"  # any Open line containing an IP
    ]
    matches = []
    for pat in patterns:
        matches.extend(re.findall(pat, output))
    if not matches:
        logger.debug(f"Discovery output (no IP matches):\n{output}")
    for match in matches:
        try:
            ip_obj = ipaddress.ip_address(match)
        except ValueError:
            continue
        if ip_obj in network and ip_obj != network.network_address and ip_obj != network.broadcast_address:
            ips.add(str(ip_obj))
    sorted_ips = sorted(ips, key=lambda ip: int(ipaddress.ip_address(ip)))
    if sorted_ips:
        logger.info(f"Discovery found {len(sorted_ips)} host(s) in {cidr_str}.")
    else:
        logger.warning(f"Discovery found no hosts in {cidr_str}.")
    return sorted_ips

def build_target_list(target, logger):
    if "/" in target:
        try:
            network = ipaddress.ip_network(target, strict=False)
        except ValueError:
            logger.error(f"Invalid network provided: {target}")
            sys.exit(1)
        logger.info(
            f"Starting discovery for {target}."
        )
        hosts = discover_hosts_in_network(network, target, logger)
        if not hosts:
            logger.error(f"No usable hosts found in network {target}.")
            sys.exit(1)
        logger.debug(f"Expanded {target} to {len(hosts)} host(s).")
        return hosts
    single = resolve_target_ip(target, logger)
    return [single]

def run_scan_for_target(target_ip, args, config, logger):
    work_dir, notes_dir = prepare_output_dir(args, config, target_ip)

    logger.info(f"Beginning scan workflow for {target_ip}.")
    logger.debug(f"Output directory: {notes_dir}")
    logger.debug(f"Config path: {CONFIG_PATH}")

    rust_ports = run_rustscan_twice(target_ip, logger, work_dir)
    ports = filter_ports(rust_ports, EXCLUDED_PORTS)
    run_nmap_udp(target_ip, work_dir, logger)
    run_nmap_tcp(target_ip, ports, work_dir, logger)
    if 445 in ports:
        run_nxc_hosts(target_ip, work_dir, logger)
        run_nxc_shares(target_ip, work_dir, logger)
    else:
        logger.debug("Skipping SMB enumeration; port 445 not open.")
    convert_markdown_to_html(work_dir, notes_dir, logger)
    copy_markdown_artifacts(work_dir, notes_dir, logger)

    logger.info(f"Scan workflow completed successfully for {target_ip}.")
    return ports

def copy_markdown_artifacts(work_dir, notes_dir, logger):
    os.makedirs(notes_dir, exist_ok=True)
    for name in os.listdir(work_dir):
        if not name.endswith(".html"):
            continue
        src = os.path.join(work_dir, name)
        dst = os.path.join(notes_dir, name)
        try:
            shutil.copy2(src, dst)
            ensure_user_ownership(dst, logger)
            logger.debug(f"Copied {src} -> {dst}")
        except OSError as exc:
            logger.error(f"Failed to copy {src} to notes dir: {exc}")

def resolve_hostname_for_summary(ip, logger):
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
    except (socket.herror, socket.gaierror, OSError):
        hostname = None
    if hostname and hostname.strip() == ip:
        hostname = None
    if hostname:
        logger.debug(f"Resolved {ip} to hostname {hostname} for summary.")
    return hostname

def log_scan_summary(summaries, logger):
    if not summaries:
        return
    logger.info("Scan summary:")
    for ip, ports in summaries:
        port_list = ",".join(map(str, ports)) if ports else "none"
        hostname = resolve_hostname_for_summary(ip, logger)
        if hostname:
            logger.info(f"{ip} | {hostname} | {port_list}")
        else:
            logger.info(f"{ip}: {port_list}")

def get_service_for_port(port):
    """Determine service name for a given port based on SERVICE_PORTS mapping."""
    for service, ports_str in SERVICE_PORTS.items():
        if str(port) in ports_str.split(","):
            return service
    return "unknown"

def generate_network_diagram(summaries, notes_dir, logger):
    """Generate an interactive HTML network diagram showing hosts and open ports."""
    if not summaries:
        logger.debug("No summaries available; skipping diagram generation.")
        return
    
    os.makedirs(notes_dir, exist_ok=True)
    
    # Build node and link data for visualization
    nodes = []
    links = []
    node_ids = set()
    
    for idx, (ip, ports) in enumerate(summaries):
        node_id = f"host_{idx}"
        hostname = resolve_hostname_for_summary(ip, logger)
        label = f"{ip}\n{hostname}" if hostname else ip
        
        nodes.append({
            "id": node_id,
            "label": label,
            "ip": ip,
            "hostname": hostname or "",
            "ports": sorted(ports) if ports else []
        })
        node_ids.add(node_id)
    
    # Generate HTML with embedded SVG visualization
    html_content = generate_diagram_html(nodes, logger)
    
    diagram_path = os.path.join(notes_dir, "network-diagram.html")
    with open(diagram_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    ensure_user_ownership(diagram_path, logger)
    logger.info("Network diagram saved.")
    return diagram_path

def generate_diagram_html(nodes, logger):
    """Generate the HTML content for the network diagram with embedded D3.js visualization."""
    
    # Prepare data for JSON serialization
    nodes_json = json.dumps(nodes)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Scan Diagram</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            /* Light grey to brown gradient per user's request */
            background: linear-gradient(135deg, #e9e9e9 0%, #8b5e3c 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .container {{
            width: 100%;
            max-width: 1400px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            /* Match header to the requested light grey -> brown theme */
            background: linear-gradient(135deg, #f5f5f5 0%, #7a4e36 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        
        .header p {{
            margin: 0;
            opacity: 0.9;
        }}
        
        #diagram {{
            width: 100%;
            height: 600px;
            background: #f8f9fa;
            position: relative;
        }}
        
        svg {{
            width: 100%;
            height: 100%;
        }}
        
        .node {{
            cursor: pointer;
            stroke: #333;
            stroke-width: 2px;
        }}
        
        .node circle {{
            fill: #4a90e2;
            transition: fill 0.3s ease;
        }}
        
        .node:hover circle {{
            fill: #2e5c8a;
            filter: drop-shadow(0 0 8px rgba(74, 144, 226, 0.6));
        }}
        
        .node text {{
            pointer-events: none;
            font-size: 12px;
            fill: #333;
            text-anchor: middle;
            font-weight: bold;
        }}
        
        .link {{
            stroke: #999;
            stroke-opacity: 0.6;
            stroke-width: 1.5px;
        }}
        
        .tooltip {{
            position: absolute;
            padding: 12px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 6px;
            font-size: 13px;
            pointer-events: none;
            display: none;
            z-index: 1000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        
        .tooltip-title {{
            font-weight: bold;
            margin-bottom: 8px;
            border-bottom: 1px solid #666;
            padding-bottom: 4px;
        }}
        
        .tooltip-content {{
            font-family: 'Courier New', monospace;
            line-height: 1.4;
        }}
        
        .port-item {{
            display: flex;
            justify-content: space-between;
            padding: 2px 0;
        }}
        
        .port-number {{
            color: #4fc3f7;
            font-weight: bold;
        }}
        
        .service-name {{
            color: #81c784;
            margin-left: 12px;
        }}
        
        .controls {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .info {{
            font-size: 14px;
            color: #666;
        }}
        
        .info strong {{
            color: #333;
        }}
        
        button {{
            padding: 10px 20px;
            background: #8b5e3c; /* brown button */
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s ease;
        }}
        
        button:hover {{
            background: #6a432b;
        }}
        
        .legend {{
            padding: 20px 30px;
            background: white;
            border-top: 1px solid #e0e0e0;
            font-size: 13px;
            color: #666;
        }}
        
        .legend-item {{
            display: inline-block;
            margin-right: 25px;
            margin-bottom: 10px;
        }}
        
        .legend-circle {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #8b5e3c; /* brown legend */
            border: 1px solid #333;
            margin-right: 6px;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Network Scan Diagram</h1>
            <p>Interactive visualization of scanned hosts and services</p>
        </div>
        
        <div id="diagram"></div>
        <div class="tooltip" id="tooltip"></div>
        
        <div class="controls">
            <div class="info">
                <strong id="nodeCount">0</strong> host(s) scanned
            </div>
            <button onclick="resetZoom()">Reset View</button>
        </div>
        
        <div class="legend">
            <div class="legend-item">
                <span class="legend-circle"></span>
                <span>Host Node - Click to see details</span>
            </div>
            <div class="legend-item">
                Hover over a node to view open ports and services
            </div>
        </div>
    </div>
    
    <script>
        const nodes = {nodes_json};
        
        function getServiceForPort(port) {{
            const serviceMap = {{
                22: 'SSH',
                445: 'SMB',
                80: 'HTTP',
                443: 'HTTPS',
                3306: 'MySQL',
                1433: 'MSSQL',
                5985: 'WinRM',
                5986: 'WinRM',
                3389: 'RDP',
                21: 'FTP',
                2049: 'NFS',
                88: 'Kerberos',
                11211: 'Memcached',
                25: 'SMTP',
                110: 'POP3',
                143: 'IMAP',
                389: 'LDAP',
                123: 'NTP',
                6379: 'Redis',
                5432: 'PostgreSQL',
                9200: 'Elasticsearch',
                9300: 'Elasticsearch',
                27017: 'MongoDB',
                9042: 'Cassandra',
                9092: 'Kafka',
                5672: 'RabbitMQ',
                15672: 'RabbitMQ',
                5900: 'VNC',
                5060: 'SIP',
                5061: 'SIP'
            }};
            return serviceMap[port] || 'Unknown';
        }}
        
        function initializeDiagram() {{
            const width = document.getElementById('diagram').clientWidth;
            const height = document.getElementById('diagram').clientHeight;
            
            const svg = d3.select('#diagram')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            const g = svg.append('g');
            
            // Add zoom behavior
            const zoom = d3.zoom()
                .on('zoom', (event) => {{
                    g.attr('transform', event.transform);
                }});
            
            svg.call(zoom);
            
            // Create force simulation
            const simulation = d3.forceSimulation(nodes)
                // a bit stronger repulsion to accommodate larger bubbles
                .force('charge', d3.forceManyBody().strength(-450))
                .force('center', d3.forceCenter(width / 2, height / 2))
                // larger collision radius so big bubbles don't overlap
                .force('collision', d3.forceCollide(90));
            
            // Create links (not used visually, but helps layout)
            const link = g.selectAll('.link')
                .data([])
                .enter()
                .append('line')
                .attr('class', 'link');
            
            // Create nodes
            const node = g.selectAll('.node')
                .data(nodes, d => d.id)
                .enter()
                .append('g')
                .attr('class', 'node')
                .call(d3.drag()
                    .on('start', dragStarted)
                    .on('drag', dragged)
                    .on('end', dragEnded));
            
            node.append('circle')
                // increased default radius per user's request
                .attr('r', 60)
                .attr('fill', '#8b5e3c')
                .attr('stroke', '#5a3f2a')
                .attr('stroke-width', 2);
            
            node.append('text')
                .attr('dy', '0.3em')
                .attr('text-anchor', 'middle')
                .style('font-size', '14px')
                .text(d => {{
                    if (d.hostname) {{
                        return d.hostname.split('.')[0];
                    }}
                    return d.ip.split('.').slice(-1)[0];
                }});
            
            // Add hover events
            node.on('mouseenter', function(event, d) {{
                const tooltip = document.getElementById('tooltip');
                let content = '<div class="tooltip-title">' + d.ip;
                if (d.hostname) content += '<br/>' + d.hostname;
                content += '</div><div class="tooltip-content">';
                
                if (d.ports && d.ports.length > 0) {{
                    d.ports.forEach(port => {{
                        const service = getServiceForPort(port);
                        content += '<div class="port-item"><span class="port-number">' + port + 
                                 '</span><span class="service-name">' + service + '</span></div>';
                    }});
                }} else {{
                    content += '<div>No open ports detected</div>';
                }}
                content += '</div>';
                
                tooltip.innerHTML = content;
                tooltip.style.display = 'block';
                
                const rect = this.getBoundingClientRect();
                tooltip.style.left = (rect.right + 10) + 'px';
                tooltip.style.top = (rect.top - 10) + 'px';
                
                d3.select(this).select('circle')
                    .transition()
                    .duration(200)
                    .attr('r', 75);
            }})
            .on('mouseleave', function(event, d) {{
                document.getElementById('tooltip').style.display = 'none';
                d3.select(this).select('circle')
                    .transition()
                    .duration(200)
                    .attr('r', 60);
            }});
            
            // Update simulation
            simulation.on('tick', () => {{
                node.attr('transform', d => `translate(${{d.x}}, ${{d.y}})`);
            }});
            
            // Update node count
            document.getElementById('nodeCount').textContent = nodes.length;
            
            window.simulation = simulation;
            window.svg = svg;
        }}
        
        function dragStarted(event, d) {{
            if (!event.active) window.simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragEnded(event, d) {{
            if (!event.active) window.simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        function resetZoom() {{
            const width = document.getElementById('diagram').clientWidth;
            const height = document.getElementById('diagram').clientHeight;
            window.svg.transition()
                .duration(750)
                .call(d3.zoom().transform, d3.zoomIdentity.translate(0, 0));
        }}
        
        // Initialize diagram when page loads
        document.addEventListener('DOMContentLoaded', initializeDiagram);
    </script>
</body>
</html>
"""
    return html_template

def scan_targets(targets, args, config, logger):
    """Run the scan workflow across all targets and collect results."""
    summaries = []
    notes_dir_base = None
    
    for target_ip in targets:
        ports = run_scan_for_target(target_ip, args, config, logger)
        summaries.append((target_ip, ports))
        if notes_dir_base is None:
            notes_dir_base = config.get("OUTPUT_DIR")
    return summaries, notes_dir_base

def finalize_results(summaries, targets, notes_dir_base, logger):
    """Log the summary and generate the network diagram if possible."""
    diagram_dir = os.getcwd()
    logger.debug(f"Saving network diagram to working directory: {diagram_dir}")
    generate_network_diagram(summaries, diagram_dir, logger)
    log_scan_summary(summaries, logger)

def main():
    args = parse_args()
    config = DEFAULT_CONFIG.copy()

    logger, log_file_path = configure_logging(args, config)
    handle_log_option(args, log_file_path)

    targets = build_target_list(args.target, logger)
    logger.info(f"Processing {len(targets)} target(s).")

    summaries, notes_dir_base = scan_targets(targets, args, config, logger)
    finalize_results(summaries, targets, notes_dir_base, logger)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
