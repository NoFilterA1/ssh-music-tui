![SSH CAVA Spotify Control](./assets/banner.png)

# 🔊 SSH Terminal Music Controller with CAVA
> 🇬🇧 English | [🇷🇺 Русский](./README.ru.md)

![Project](https://img.shields.io/badge/Terminal%20Visualizer-SSH%20Control-ff0033?style=for-the-badge&labelColor=660000)

### 🚨 THIS IS NOT JUST A SCRIPT — IT’S A TERMINAL PARTY WITH VISUALS!

---

## 🎯 Description

This is a **Python-based interactive TUI** (Terminal User Interface) for controlling music remotely over SSH.  
It combines **Spotify control**, **system volume adjustment**, and a **live CAVA visualizer** — all in one colorful terminal dashboard.

---

## 🚀 Features

✅ Real-time **CAVA visualizer** with red bars & white outline.  
✅ Adjustable number of CAVA bars with ← / → keys.  
✅ **Big clickable buttons** — perfect for touch terminals in Termux.  
✅ **Track title autoscroll** for long names.  
✅ Full **Spotify control** with `playerctl`.  
✅ Volume control via **PulseAudio**.  
✅ Runs perfectly over SSH, including Termux on Android.  

---

## 🛠️ Installation

### 📂 Clone the repo
```bash
git clone https://github.com/69lihtajc96/ssh-music-tui.git
cd ssh-music-tui
````

### 📋 Install dependencies

* **Debian/Ubuntu/Kali**:

```bash
sudo apt install python3 python3-pip pulseaudio-utils playerctl cava
pip3 install pulsectl
```

* **Arch Linux**:

```bash
sudo pacman -S python python-pip pulseaudio playerctl cava
pip install pulsectl
```

---

## 🎯 Usage

```bash
python3 spotify_sound_control.py
```

**Controls:**

* **Mouse click** → activate buttons (Prev / Play-Pause / Next / Volume +/-)
* **← / →** → change number of CAVA bars
* **q** or **ESC** → exit

---

## ❗ Troubleshooting

🚫 **No CAVA output** → Make sure [`cava`](https://github.com/karlstav/cava) is installed and works standalone.

🔊 **No volume change** → Install [`pulsectl`](https://pypi.org/project/pulsectl/) and ensure PulseAudio is running.

🎵 **Spotify not responding** → Ensure [`playerctl`](https://github.com/altdesktop/playerctl) can control your player:

```bash
playerctl -p spotify play-pause
```

---

## 📜 License

[MIT License](./LICENSE) — Have fun and make your terminal sing! 🎶


