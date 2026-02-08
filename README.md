# Comic Downloader 

A gui to download raw image

## Features

- **image extraction** - extract image and downloads it
- **Playwright browser support** (recommended) - handles JavaScript, lazy-loading, and etc.
- **Fallback to requests** when Playwright is not installed
- **Automatic folder naming** - comic title / chapter name based on page metadata
- **Filtering options**:
  - Exclude GIFs
  - Skip tiny images (<15 KB - usually ads/logos)
  - Aggressive filtering of comment-section / social images
- **Export formats**:
  - Individual images (jpg/png/webp)
  - **CBZ** (standard comic book archive – ZIP)
  - PDF (requires Pillow)
  - EPUB (requires Pillow + ebooklib)
- Test URL - (shows how many images would be found without downloading)


## Usage
0. Install Package
```
pip install -r requirements.txt
```

1. Paste the **chapter URL** (ex: https://comic.naver.com/webtoon/detail?titleId=758150&no=270&week=sun)
2. Choose save location (defaults to `~/Downloads/Comics`)
3. Keep **Use Playwright browser** checked unless you have a specific reason not to
4. Select what export formats you want.
5. Click **Start Download** or first use **Test URL** to preview results

## Recommended Settings for Most Sites

| Setting                        | Recommended       | Reason                                      |
|-------------------------------|-------------------|---------------------------------------------|
| Use Playwright browser        | ☑ Checked         | Handles lazy-load / JS / protection    |
| Exclude GIFs                  | ☑ Checked         | Very few comics use real GIFs               |
| Skip tiny images              | ☑ Checked         | Removes most ads, logos, watermarks         |
| Aggressive comment filtering  | ☑ Checked         | Avoids comment avatars / reaction images    |
| Generate CBZ                  | ☑ Checked         | compatibility with comic readers       |
| Generate PDF / EPUB           | Optional          | Larger files, slower to create              |

## Supported Sites I tested on (Im working on to make it support more sites)
- https://comic.naver.com/index
- https://page.kakao.com/
- https://www.twmanga.com/
Above^ - are raw website (works 100%)

- https://comix.to/ (still needs improvement and doesnt download all the images)
- https://cocomic.co/
- https://mangaball.net/ (a few works i did test, but some wont download or show)
- https://atsu.moe/
- https://asuracomic.net/
(Could work for more but idk havent tested it)


