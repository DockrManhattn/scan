#!/bin/bash
# dockrmanhattn@gmail.com
# v 0.1.0
# This script prompts for sudo password to check for SNMP
# Usage: scan 192.168.1.100

IP=$1

if ! [[ $IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    IP=$(getent hosts $IP | awk '{ print $1 }')
    if [[ -z "$IP" ]]; then
        echo "Could not resolve domain to an IP address."
        exit 1
    fi
fi
sudo echo -e "\033[0;33mScanning $IP\033[0m"

sudo grc nmap -sU -Pn -p 161 $IP -oN 001-scan-snmp.md

RUSTSCAN_OUTPUT=$(rustscan -a "$IP" --ulimit 5000 --scripts none)

PORTS=$(echo "$RUSTSCAN_OUTPUT" | grep -oP 'Open \d+\.\d+\.\d+\.\d+:\K\d+' | sort -u | tr '\n' ',' | sed 's/,$//')

if [[ -z "$PORTS" ]]; then
    echo "No ports found in the scan results."
    exit 1
fi

EXCLUDED_PORTS="0,1,38"
PORTS=$(echo "$PORTS" | tr ',' '\n' | grep -v -E "^($(echo $EXCLUDED_PORTS | tr ',' '|'))$" | tr '\n' ',' | sed 's/,$//')

if [[ -n "$PORTS" ]]; then
    grc nmap -sCV -Pn -oN 002-scan-nmap.md -p $PORTS $IP
else
    echo "No valid ports to scan with Nmap."
    exit 1
fi

echo "nxc smb $IP -u '' -p '' --shares" > 003-scan-nxc.md
nxc smb $IP -u '' -p '' --shares | tee -a 003-scan-nxc.md
echo "" >> 003-scan-nxc.md
echo "nxc smb $IP -u 'a' -p '' --shares" >> 003-scan-nxc.md
nxc smb $IP -u 'a' -p '' --shares | tee -a 003-scan-nxc.md
