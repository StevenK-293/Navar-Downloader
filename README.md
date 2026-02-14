# Comic Downloader

A universal comic downloader image that grabs manga, manhwa, and manhua image from pretty much any website, this started as a simple tool for raw sites like Naver and Kakao, but now it evolved into something that just works everywhere. Why? Because manually downloading images one by one took way long for me.

##  Features

* **Smart image extraction** - automatically finds and downloads all comic images from any chapter page
* **browser mode** - uses Playwright to handle JavaScript-heavy sites, lazy loading, and anti-scraping protection
* **Direct HTTP fallback** - switches to simple requests if browser mode isn't available
* **Live download info** - shows image URLs and file sizes as they download
* **Auto-naming** - creates folders based on comic title and chapter metadata
* **Smart filtering**:
  * Excludes GIFs (unless you really want them)
  * Skips tiny images under 15 KB (goodbye ads and logos)
  * Filters out comment avatars and social media junk
* **Multiple export formats**:
  * Individual images (JPG / PNG / WEBP)
  * **CBZ** - standard comic book archive, works with all readers
  * PDF - requires Pillow
  * EPUB - requires Pillow + ebooklib
* **Test URL** - preview how many images will be found before actually downloading

## Quick Start

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (needed for browser mode)
playwright install
```

### How to Use

1. Run the app:
   ```bash
   python index.py
   ```

2. Paste your **chapter URL**
   - Examples:
     - `https://comic.naver.com/webtoon/detail?titleId=758150&no=270&week=sun`
     - `https://page.kakao.com/content/54727849/viewer/54730829`
     - `https://comix.to/title/nk9re-raising-villains-the-right-way/8205015-chapter-22`

3. Choose where to save (defaults to `~/Downloads/Comics`)

4. Keep **Use Playwright browser** enabled (recommended for most sites)

5. Select your export formats (CBZ is the most compatible)

6. Hit **Start Download** or **Test URL** to preview first

## Recommended Settings (Most Sites)

| Setting                      | Recommended | Reason                                   |
| ---------------------------- | ----------- | ---------------------------------------- |
| Use Playwright browser       | ☑ Checked   | Handles JS, lazy loading, and protection |
| Exclude GIFs                 | ☑ Checked   | Most comics don’t use real GIFs          |
| Skip tiny images             | ☑ Checked   | Filters ads, logos, and watermarks       |
| Aggressive comment filtering | ☑ Checked   | Avoids avatars and reaction images       |
| Generate CBZ                 | ☑ Checked   | Best compatibility with comic readers    |
| Generate PDF / EPUB          | Optional    | Larger files, slower generation          |

## Supported Sites (Tested)

### Raw Sites (raw image sites)

* [https://comic.naver.com/index](https://comic.naver.com/index)
* [https://page.kakao.com/](https://page.kakao.com/)
* [https://www.twmanga.com/](https://www.twmanga.com/)

### Not raw sites

* [https://comix.to/](https://comix.to/)  (should work now)
* [https://cocomic.co/](https://cocomic.co/)
* [https://mangaball.net/](https://mangaball.net/) (should work now)
* [https://atsu.moe/](https://atsu.moe/)
* [https://asuracomic.net/](https://asuracomic.net/)
* [https://manhwazone.to/](https://manhwazone.to/)
* [https://flamecomics.xyz/](https://flamecomics.xyz/)
* [https://luacomic.org/](https://luacomic.org/)
* [https://kuramanga.com/](https://kuramanga.com/)

> **Note:** Many other sites should work too, but these are the ones i actually tested. If it doesn't work on your favorite site, let me know so i can add it.
