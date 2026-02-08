# Comic Downloader

Was a simple tool to extract & download image from raw sites like navar or kako, but i just made it so you can extract image & download image from many sites now idk why just did it.

## Features

* **Image extraction** - finds and downloads comic images from a chapter page
* **Playwright browser support (recommended)** - handles JavaScript, lazy loading, and site protections
* **Requests fallback** - used automatically if Playwright is not installed
* **Automatic folder naming** - uses comic title and chapter name from page metadata
* **Filtering options**:

  * Exclude GIFs
  * Skip tiny images (<15 KB, usually ads or logos)
  * Aggressive filtering for comment-section and social images
* **Export formats**:

  * Individual images (JPG / PNG / WEBP)
  * **CBZ** (standard comic book archive – ZIP)
  * PDF (requires Pillow)
  * EPUB (requires Pillow + ebooklib)
* **Test URL mode** – preview how many images will be found without downloading

## Usage

### 0. Install dependencies

```bash
pip install -r requirements.txt
```

### 1. Download a chapter

1. Paste the **chapter URL**

   * Example:
     `https://comic.naver.com/webtoon/detail?titleId=758150&no=270&week=sun`
   * Example 2:
     `https://page.kakao.com/content/54727849/viewer/54730829`
2. Choose a save location (defaults to `~/Downloads/Comics`)
3. Keep **Use Playwright browser** enabled unless you have a specific reason not to
4. Select your export formats
5. Click **Start Download**, or use **Test URL** first to preview results

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

* [https://comix.to/](https://comix.to/) (does not download all images yet)
* [https://cocomic.co/](https://cocomic.co/)
* [https://mangaball.net/](https://mangaball.net/) (some chapters fail or don’t display)
* [https://atsu.moe/](https://atsu.moe/)
* [https://asuracomic.net/](https://asuracomic.net/)

> Other sites may work, but they have not been fully tested yet.
