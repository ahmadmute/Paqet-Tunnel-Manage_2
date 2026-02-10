# Paqet Tunnel Manager | [📄 فارسی](README.fa.md)

> Management script for **paqet**: a raw socket, KCP-based tunnel for firewall/DPI bypass.  
> Supports **Kharej (external)** and **Iran (client)** setups.

**Maintained by:** [ahmadmute](https://github.com/ahmadmute) · **Based on:** [Paqet](https://github.com/hanselime/paqet) (hanselime) · **Manager idea:** [behzadea12](https://github.com/behzadea12)

---

## Quick Start

Run on **both servers** as **root**:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ahmadmute/Paqet-Tunnel-Manage_2/main/paqet-manager.sh)
```

Then choose **option 0**, then **option 1** to install prerequisites.

---

## Table of Contents

* [Quick Start](#quick-start)
* [Fork This Repo](#fork-this-repo)
* [What's Improved / Optimizations](#whats-improved--optimizations)
* [Installation Steps](#installation-steps)
  * [Step 1: Server (Kharej)](#step-1-setup-server-kharej--vpn-server)
  * [Step 2: Client (Iran)](#step-2-setup-server-iran--cliententry-point)
* [Advanced Configuration (KCP Modes)](#advanced-configuration-kcp-modes)
* [Network Optimization](#network-optimization-optional)
* [Included Tools](#included-tools)
* [Troubleshooting](#troubleshooting-paqet-installation-issues)
* [Web Dashboard](#web-dashboard)
* [Need Help](#%EF%B8%8F-need-help)
* [Requirements](#requirements)
* [Screenshots](#-script-screenshots)
* [License](#license)
* [Credits](#credits)

---

## Fork This Repo

You can fork this project and use your own copy.

1. **Fork on GitHub**  
   Click **Fork** at the top of [github.com/ahmadmute/Paqet-Tunnel-Manage_2](https://github.com/ahmadmute/Paqet-Tunnel-Manage_2).  
   You’ll get a copy under your account, e.g. `https://github.com/YOUR_USERNAME/Paqet-Tunnel-Manage_2`.

2. **Use your install URL**  
   After forking, your one-line install will be:
   ```bash
   bash <(curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/Paqet-Tunnel-Manage_2/main/paqet-manager.sh)
   ```
   Replace `YOUR_USERNAME` with your GitHub username.

3. **Optional: edit and push**  
   Clone your fork, change `paqet-manager.sh` or the READMEs, then push to `main`.  
   The install command above will always use the latest `main` branch of your fork.

**Note:** Please keep credits for [Paqet](https://github.com/hanselime/paqet) (hanselime) and the original [Manager](https://github.com/behzadea12) (behzadea12) in the script and README.

---

## What's Improved / Optimizations

In this fork (ahmadmute) the following improvements were made:

| Area | Change |
|------|--------|
| **Port handling** | All ports (listen, server, forward, V2Ray/OpenVPN/L2TP/SSTP) are **trimmed** (spaces/tabs removed) and **validated** (1–65535). Prevents broken configs when a port is entered with spaces or invalid values. |
| **Config reliability** | Ports written to YAML are always clean numbers, so server and client connect correctly and iptables rules use the right port. |
| **UI / Banner** | Redesigned banner with clearer layout, colors (cyan/green/yellow), and credits. Main menu has separators and consistent spacing. |
| **Credits** | Script and README clearly credit: **Paqet** (hanselime), **Manager idea** (behzadea12), **This fork** (ahmadmute). |
| **Port list** | Forward/V2Ray/OpenVPN/L2TP/SSTP port lists (e.g. `9090, 443, 1194`) are normalized: extra commas and spaces removed before use. |
| **UDP forwarding (KCP)** | After TCP ports, the script asks for **UDP ports** (comma-separated). Enter ports used by KCP or V2Ray over UDP so they are forwarded over the tunnel. |

---

## Installation Steps

### Step 1: Setup Server (Kharej – VPN Server)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ahmadmute/Paqet-Tunnel-Manage_2/main/paqet-manager.sh)
```

1. **Option 2** (Kharej)
2. Custom name for the tunnel
3. Press Enter *(auto)* for interface, local IP, gateway MAC
4. **Listen port** (e.g. `555`)
5. Save the **secret key**, press **Y**
6. KCP: option 1 (or custom), conn value, MTU (e.g. 1350)
7. **Option 2**, then service port(s): V2Ray/OpenVPN/L2TP/SSTP – e.g. `9090` or `9090,443,1194`

---

### Step 2: Setup Server (Iran – Client/Entry Point)

1. **Option 3** (Iran)
2. Kharej server **IP**
3. Same **port** as Kharej (e.g. `555`)
4. **Secret key** from Kharej
5. Custom name, then Enter for auto fields
6. KCP settings (same as Kharej)
7. Forward ports TCP (same as server): e.g. `9090` or `9090,443,1194` for V2Ray/OpenVPN/L2TP/SSTP  
8. UDP ports (optional): for KCP or V2Ray UDP – comma-separated (e.g. `9999`) or Enter to skip.

---

## Config on the Foreign Server (Kharej)

Paqet config on the **foreign server (Kharej)** is stored at:

- **Path:** `/etc/paqet/<config_name>.yaml`  
  e.g. if you used the name `server`: `/etc/paqet/server.yaml`

**Typical server contents:**
- `role: "server"`
- `listen.addr` – port Paqet listens on (e.g. `:555`)
- `transport.kcp.key` – secret key (same one you enter on the Iran server)

**View/edit:**
- From the script menu: **Option 4 (List Services)** → **Manage** → **View config**
- Directly in terminal:
  ```bash
  sudo cat /etc/paqet/server.yaml
  sudo nano /etc/paqet/server.yaml   # edit
  sudo systemctl restart paqet-server   # after editing
  ```

The **Iran server (client)** has its own config at `/etc/paqet/<name>.yaml` with `role: "client"` and `server.addr` / `forward:` sections.

---

## Advanced Configuration (KCP Modes)

| Mode    | Speed   | Latency | Resources |
|--------|--------|---------|-----------|
| normal | Normal | Normal  | Low       |
| **fast** | Balanced | Low   | Normal *(recommended)* |
| fast2  | High   | Lower   | Moderate  |
| fast3  | Max    | Very low| High      |
| manual | Custom | Custom  | Custom    |

**What is KCP on the foreign server?**  
On the Kharej server, **KCP** is the **tunnel transport** protocol: traffic between the Iran server and the foreign server uses KCP over the **same listen port** (e.g. `555`). There is no separate “KCP port”; the port you set as **Listen port** when setting up the Kharej server is the KCP port. The client (Iran server) connects to `foreign_IP:555` and the tunnel runs over KCP.

---

## Improving tunnel speed

If tunnel speed is low, try these (in order of impact):

| Action | Notes |
|--------|--------|
| **1. BBR on Kharej** | Menu → **Option 7** → install **BBR**. Changes TCP congestion control and often improves throughput. Reboot may be required after install. |
| **2. Stronger KCP mode** | If you use `normal` or `fast`, recreate config and choose **fast2** or **fast3**. fast3 gives highest speed and lowest latency but uses more CPU. |
| **3. Higher conn** | Increase **conn** from 1 to **2–4** (or up to 32) for parallel KCP streams. When the script asks for "conn" during server/client setup, enter a higher value. Both server and client must use the same conn and KCP mode. |
| **4. MTU** | Default 1350 is fine. If you have no packet errors, try **1400** or **1450**. On lossy paths, lower MTU (e.g. 1200) can be more stable. |
| **5. Encryption** | **aes-128-gcm** is often faster than **aes**. **none** is fastest but not DPI-safe; use only for testing. |
| **6. Kharej server** | Server location and bandwidth matter. A closer, higher-bandwidth Kharej usually gives better end-user speed. |

After any KCP change (mode, conn, MTU, block), both server and client configs must match and both services must be restarted.

---

## Network Optimization (Optional)

Run the script → **Option 7**:

1. **BBR** – TCP congestion *(Kharej)*
2. **DNS Finder** – Best DNS for Iran *(Iran)*
3. **Mirror Selector** – Fastest APT mirror *(Iran)*

---

## Included Tools

* [BBR (across)](https://github.com/teddysun/across/) – TCP congestion control
* [IranDNSFinder](https://github.com/alinezamifar/IranDNSFinder) – DNS for Iran
* [DetectUbuntuMirror](https://github.com/alinezamifar/DetectUbuntuMirror) – APT mirror (Ubuntu/Debian)

---

## Troubleshooting: Paqet Installation Issues

### Download / binary not found

If Paqet fails to install:

1. Download manually: [hanselime/paqet releases](https://github.com/hanselime/paqet/releases)  
   Use `paqet-linux-amd64-*.tar.gz` (x86_64) or `paqet-linux-arm64-*.tar.gz` (arm64).
2. Put the file in: `/root/paqet/`  
   `mkdir -p /root/paqet`
3. Run the manager again – it will detect and install from that folder.

### GLIBC_2.32 or GLIBC_2.34 not found

If the service fails with:

```text
/usr/local/bin/paqet: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.34' not found
```

the pre-built Paqet binary needs a **newer glibc** than your system has (e.g. Ubuntu 18.04, Debian 10).

**Options:**

1. **Upgrade the OS** to a distro with glibc 2.34+:
   - **Ubuntu 22.04** or newer  
   - **Debian 12** or newer  
   Then reinstall Paqet with the manager (option 0).

2. **Build Paqet from source** on the same machine (so it uses your current glibc):
   ```bash
   apt install -y golang git
   git clone https://github.com/hanselime/paqet.git && cd paqet
   go build -o paqet ./cmd/paqet
   sudo cp paqet /usr/local/bin/paqet
   sudo chmod +x /usr/local/bin/paqet
   ```
   Then start your Paqet service again (e.g. from the manager: List Services → Manage → Start).

3. **Use a VPS with a newer distro** (e.g. Ubuntu 22.04) and install Paqet there.

### `bind: address already in use` (port in use)

If Paqet fails with:

```text
failed to bind TCP socket on 0.0.0.0:8443: bind: address already in use
```

the **port** (e.g. 8443) is already in use on the same machine by another program, or the **same port** was added twice in the forward list.

**Fix:**

1. **Check what uses the port:** `ss -tuln | grep 8443` or `lsof -i :8443`. Stop that service or remove that port from the Paqet forward list and use another port.
2. **Remove duplicate port:** If a port (e.g. 8443) appears twice in your list, edit the config and remove the duplicate, or reconfigure the client (option 3) and enter ports **without duplicates**. New script versions auto-deduplicate.
3. **Edit config:** `nano /etc/paqet/your_config.yaml` – under `forward:` remove the duplicate listen entry for that port, then `systemctl restart paqet-your_config`.

---

## Web Dashboard

From the script menu choose **Option 10 – Web Dashboard**. Open in browser: **http://YOUR_SERVER_IP:8880/login**

- **Login page** – Looks like a normal “Secure Portal” sign-in page (helps avoid DPI suspicion). Use any **username** and password **`paqet`** or **`admin`**.
- **Dashboard** (after login) – Status of all Paqet services, logs (`journalctl`), YAML configs, and Restart buttons.
- **Custom password:** set env `PAQET_DASHBOARD_PASS=yourpass` before starting the dashboard.

Requires **python3**. If `paqet-dashboard.py` is not next to the script, it is downloaded from the repo to `/tmp` when you first run the dashboard.

### Decoy website (port 443)

From the menu choose **Option 11 – Decoy website**. A fake corporate/portal page is served on port **443** (or another port you choose). DPI or scanners see a normal “Secure Portal” site; no user action needed. Useful so traffic on 443 looks like a regular website. Run as root for port 443.

### Web Dashboard / Decoy as service (always on)

- **Option 12 – Web Dashboard as service:** Installs the dashboard as a systemd service so it runs in the background and starts on boot. You can open the URL anytime to check status, logs, and config. Stop/restart from **Option 5 (Manage Service)** → paqet-dashboard.
- **Option 13 – Decoy website as service:** Same for the decoy site on port 443 (or your chosen port). Stop/restart from **Option 5 (Manage Service)** → paqet-decoy.

---

## ⚠️ Need Help?

* **This fork:** [ahmadmute](https://github.com/ahmadmute)
* **Original manager:** [@behzad_developer](https://t.me/behzad_developer) (behzadea12)

---

## Requirements

* Linux (Ubuntu, Debian, CentOS, etc.)
* Root access
* `libpcap-dev`, `iptables`, `paqet`

---

## 📸 Script Screenshots

<details>
<summary>Main Menu</summary>
<br>
<img src="images/Main_Menu.png" width="800">
</details>

<details>
<summary>Install Paqet</summary>
<br>
<img src="images/Install_paqet.png" width="800">
</details>

<details>
<summary>List Services</summary>
<br>
<img src="images/List_Services.png" width="800">
</details>

<details>
<summary>Manage Service</summary>
<br>
<img src="images/Manage_Service.png" width="800">
</details>

<details>
<summary>Optimize Server</summary>
<br>
<img src="images/Optimize_Server.png" width="800">
</details>

---

## License

**MIT License**

---

## Credits

| Project / Person | Role |
|------------------|------|
| [hanselime/paqet](https://github.com/hanselime/paqet) | Raw packet tunnel (Paqet) |
| [behzadea12](https://github.com/behzadea12) | Original Paqet-Tunnel-Manager idea & design |
| [ahmadmute](https://github.com/ahmadmute) | This fork – maintained |

---

## 💖 Support

Using this and want to support? The original project accepts:

* **Tron (TRC20):** `TFYnorJt5gvejLwR8XQdjep1krS9Zw8pz3`

Any contribution helps. 🙏
