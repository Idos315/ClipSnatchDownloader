# ⬇ ClipSnatch

A clean, simple video downloader for macOS. Download videos from **YouTube, TikTok, Instagram, and Facebook** with one click.

Built with Python + PySide6 + yt-dlp.

---

## Message from the creator

Hey! I'm not a developer - I just wanted a clean way to download videos without dealing with annoying scammy websites and pop-up ads everywhere. So I built this with Claude AI. It does exactly what I need, and maybe it'll help you too. 🙂

Hope it works smoothly for you - and if you run into any bugs, feel free to open an issue on GitHub. I'll do my best to fix it (with Claude's help 😄).

---

## Features

- 🎬 Download from YouTube, TikTok, Instagram, Facebook (and 1800+ other sites)
- 🎵 Save as MP4, MP3, or original format
- 📋 Playlist & Instagram carousel support - pick which items to download
- 🔐 Cookie-based authentication for private/login-required content
- ⚡ Live progress bar with speed and ETA
- 🖥 Clean dark UI, no ads, no tracking

---

## Installation (macOS)

### Easy install - DMG (recommended)

1. Go to the [Releases](../../releases) page
2. Download **ClipSnatch.dmg**
3. Open the DMG, drag ClipSnatch into your Applications folder
4. Double-click to launch

> If macOS says the app is damaged or from an unidentified developer, open Terminal and run:
> ```bash
> xattr -rd com.apple.quarantine /Applications/ClipSnatch.app
> ```

---

### Build from source

If you prefer to build it yourself:

#### Requirements
- macOS 11 or later (Apple Silicon and Intel both work)
- Python 3.10 or later → [download here](https://www.python.org/downloads/) if you don't have it

#### Steps

**1. Download this project**

Click the green **Code** button → **Download ZIP** → extract it somewhere (like your Desktop).

**2. Open Terminal**

Press `Cmd + Space`, type `Terminal`, hit Enter.

**3. Navigate to the folder**

Type `cd` followed by a space, then drag the extracted `clipsnatch` folder onto the Terminal window. Hit Enter.

**4. Run the installer**

```bash
bash install.sh
```

The script will:
- Install Homebrew (if needed)
- Install ffmpeg (if needed)
- Set up Python dependencies
- Build **ClipSnatch.app** and place it on your Desktop

The whole process takes about 3-5 minutes. It may ask for your Mac password once, that's normal.

**5. Launch**

Double-click **ClipSnatch.app** on your Desktop. You can drag it to your Applications folder or Dock.

---

## How to use

1. Copy a video URL from YouTube, TikTok, Instagram, or Facebook
2. Paste it into ClipSnatch and click **Fetch Info**
3. Choose your format and quality
4. Set **Save As** to MP4 (recommended) or MP3 for audio only
5. Click **Download**

### For Instagram / Facebook / private content

Log in to the site in Chrome, Firefox, or Edge first, then:
- Check **"Use browser cookies"** and select that browser in the app

Or use the **Import cookies.txt** option with a cookies file exported from your browser.

---

## Adding a custom icon

1. Make a PNG image (1024×1024 recommended)
2. Convert it to `.icns` at [cloudconvert.com/png-to-icns](https://cloudconvert.com/png-to-icns)
3. Save it as `assets/icon.icns` inside the clipsnatch folder
4. Re-run `bash build_app.sh` to rebuild the app with the new icon

---

## Updating

Sites change their code often and downloads may stop working. To update yt-dlp:

```bash
cd /path/to/clipsnatch
source .venv/bin/activate
pip install -U yt-dlp
bash build_app.sh
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "App is damaged" warning | Run: `xattr -rd com.apple.quarantine /Applications/ClipSnatch.app` |
| Video won't play in QuickTime | Select **MP4** in the Save As dropdown |
| Instagram / Facebook won't download | Enable **Use browser cookies** and select your browser |
| Downloads suddenly stopped working | Update yt-dlp (see above) |
| App won't open at all | Re-run `bash build_app.sh` to rebuild |

---

## Project structure

```
clipsnatch/
├── main.py            # Entry point
├── ui.py              # Qt UI
├── ytdlp_service.py   # yt-dlp wrapper (fetch + download)
├── ffmpeg_service.py  # ffmpeg wrapper (MP3/MP4 conversion)
├── models.py          # Data structures
├── install.sh         # One-click installer for new users
├── build_app.sh       # Rebuilds the .app and .dmg
├── requirements.txt   # Python dependencies
└── assets/            # Place icon.icns here
```

---

## Tech stack

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - download engine
- [PySide6](https://doc.qt.io/qtforpython/) - Qt6 GUI framework
- [ffmpeg](https://ffmpeg.org/) - audio/video conversion
- [PyInstaller](https://pyinstaller.org/) - macOS app packaging
- [create-dmg](https://github.com/create-dmg/create-dmg) - DMG installer creation

---

## License

MIT - free to use, modify, and share.

> ⚠️ Only download content you have the right to download. Respect copyright and platform terms of service.
