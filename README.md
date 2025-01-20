# Scan
Type less, scan more.
## Installation
The easiest way to install this script is to run:
```bash
chmod +x ./setup.sh
./setup.sh
```
Requires sudo to check SNMP
## Usage  
```bash
scan 192.168.1.1
```
```bash
scan hostname.domain.com
```

## Example
```bash
❯ export IP='10.10.66.188'
❯ scan $IP
Scanning 10.10.66.188
Starting Nmap 7.94SVN ( https://nmap.org ) at 2025-01-05 10:10 EST
Nmap scan report for DC (10.10.66.188)
Host is up (0.13s latency).

PORT    STATE         SERVICE
161/udp open|filtered snmp

Nmap done: 1 IP address (1 host up) scanned in 1.73 seconds
Starting Nmap 7.94SVN ( https://nmap.org ) at 2025-01-05 10:10 EST
Nmap scan report for DC (10.10.66.188)
Host is up (0.14s latency).

PORT      STATE SERVICE       VERSION
53/tcp    open  domain        Simple DNS Plus
88/tcp    open  kerberos-sec  Microsoft Windows Kerberos (server time: 2025-01-05 15:10:22Z)
135/tcp   open  msrpc         Microsoft Windows RPC
139/tcp   open  netbios-ssn   Microsoft Windows netbios-ssn
389/tcp   open  ldap          Microsoft Windows Active Directory LDAP (Domain: baby2.vl0., Site: Default-First-Site-Name)
| ssl-cert: Subject: commonName=dc.baby2.vl
| Subject Alternative Name: othername: 1.3.6.1.4.1.311.25.1::<unsupported>, DNS:dc.baby2.vl
| Not valid before: 2025-01-05T14:39:42
|_Not valid after:  2026-01-05T14:39:42
|_ssl-date: TLS randomness does not represent time
445/tcp   open  microsoft-ds?
464/tcp   open  kpasswd5?
593/tcp   open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp   open  ssl/ldap      Microsoft Windows Active Directory LDAP (Domain: baby2.vl0., Site: Default-First-Site-Name)
|_ssl-date: TLS randomness does not represent time
| ssl-cert: Subject: commonName=dc.baby2.vl
| Subject Alternative Name: othername: 1.3.6.1.4.1.311.25.1::<unsupported>, DNS:dc.baby2.vl
| Not valid before: 2025-01-05T14:39:42
|_Not valid after:  2026-01-05T14:39:42
3268/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: baby2.vl0., Site: Default-First-Site-Name)
| ssl-cert: Subject: commonName=dc.baby2.vl
| Subject Alternative Name: othername: 1.3.6.1.4.1.311.25.1::<unsupported>, DNS:dc.baby2.vl
| Not valid before: 2025-01-05T14:39:42
|_Not valid after:  2026-01-05T14:39:42
|_ssl-date: TLS randomness does not represent time
3269/tcp  open  ssl/ldap      Microsoft Windows Active Directory LDAP (Domain: baby2.vl0., Site: Default-First-Site-Name)
|_ssl-date: TLS randomness does not represent time
| ssl-cert: Subject: commonName=dc.baby2.vl
| Subject Alternative Name: othername: 1.3.6.1.4.1.311.25.1::<unsupported>, DNS:dc.baby2.vl
| Not valid before: 2025-01-05T14:39:42
|_Not valid after:  2026-01-05T14:39:42
5985/tcp  open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-title: Not Found
|_http-server-header: Microsoft-HTTPAPI/2.0
9389/tcp  open  mc-nmf        .NET Message Framing
49664/tcp open  msrpc         Microsoft Windows RPC
49667/tcp open  msrpc         Microsoft Windows RPC
49671/tcp open  msrpc         Microsoft Windows RPC
49674/tcp open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
49676/tcp open  msrpc         Microsoft Windows RPC
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
| smb2-security-mode:
|   3:1:1:
|_    Message signing enabled and required
| smb2-time:
|   date: 2025-01-05T15:11:12
|_  start_date: N/A
|_clock-skew: -1s

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 98.89 seconds
SMB                      10.10.66.188    445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:baby2.vl) (signing:True) (SMBv1:False)
SMB                      10.10.66.188    445    DC               [+] baby2.vl\:
SMB                      10.10.66.188    445    DC               [-] Error enumerating shares: STATUS_ACCESS_DENIED
SMB                      10.10.66.188    445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:baby2.vl) (signing:True) (SMBv1:False)
SMB                      10.10.66.188    445    DC               [+] baby2.vl\a: (Guest)
SMB                      10.10.66.188    445    DC               [*] Enumerated shares
SMB                      10.10.66.188    445    DC               Share           Permissions     Remark
SMB                      10.10.66.188    445    DC               -----           -----------     ------
SMB                      10.10.66.188    445    DC               ADMIN$                          Remote Admin
SMB                      10.10.66.188    445    DC               apps            READ
SMB                      10.10.66.188    445    DC               C$                              Default share
SMB                      10.10.66.188    445    DC               docs
SMB                      10.10.66.188    445    DC               homes           READ,WRITE
SMB                      10.10.66.188    445    DC               IPC$            READ            Remote IPC
SMB                      10.10.66.188    445    DC               NETLOGON        READ            Logon server share
SMB                      10.10.66.188    445    DC               SYSVOL                          Logon server share
```
