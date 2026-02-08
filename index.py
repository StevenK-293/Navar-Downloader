import os
import re
import time
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from bs4 import BeautifulSoup
import threading
from urllib.parse import urlparse, urljoin
from pathlib import Path
import zipfile
PLAYWRIGHT_AVAILABLE = False
PIL_AVAILABLE = False
EPUB_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    pass

try:
    import ebooklib
    from ebooklib import epub
    EPUB_AVAILABLE = True
except ImportError:
    pass


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tooltip,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=4
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class download_comic:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Comic Downloader")
        self.root.geometry("860x760")
        self.root.resizable(True, True)

        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.home() / "Downloads" / "Comics"))
        self.use_browser_var = tk.BooleanVar(value=PLAYWRIGHT_AVAILABLE)
        self.exclude_gifs_var = tk.BooleanVar(value=True)
        self.skip_tiny_var = tk.BooleanVar(value=True)
        self.aggressive_comments_var = tk.BooleanVar(value=True)
        self.generate_pdf_var = tk.BooleanVar(value=False)
        self.generate_epub_var = tk.BooleanVar(value=False)
        self.generate_cbz_var = tk.BooleanVar(value=True)

        self.running = False
        self.total_images = 0

        self.current_status = tk.StringVar(value="Ready")
        self.progress_value = tk.DoubleVar(value=0)
        self.progress_label = tk.StringVar(value="0%")

        self.setup_ui()

        if PLAYWRIGHT_AVAILABLE:
            self.log_message("Playwright detected — browser mode enabled by default", "ok")
        else:
            self.log_message("Playwright not installed — falling back to requests", "warn")
            self.log_message("Install with: pip install playwright && playwright install", "warn")

        if PIL_AVAILABLE:
            self.log_message("Pillow detected — PDF and image processing enabled", "info")
        else:
            self.log_message("Pillow not found — PDF/EPUB disabled (pip install pillow)", "warn")

        if EPUB_AVAILABLE:
            self.log_message("ebooklib detected — EPUB export available", "info")
        else:
            self.log_message("ebooklib not installed — EPUB disabled (pip install ebooklib)", "warn")

        self.log_message("CBZ (Comic Book ZIP) export enabled", "info")
        self.log_message("Comic Downloader is ready.", "info")

    def setup_ui(self):
        main = ttk.Frame(self.root, padding="18")
        main.pack(fill=tk.BOTH, expand=True)

        # URL input
        url_lbl = ttk.Label(main, text="Chapter URL", font=("Segoe UI", 11, "bold"))
        url_lbl.grid(row=0, column=0, sticky="w", pady=(0, 4))
        Tooltip(url_lbl, "Paste the full chapter URL (Toonily, Asura, Reaper, ManhwaTop, etc.)")

        ttk.Entry(main, textvariable=self.url_var, font=("Segoe UI", 10), width=100).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )

        ttk.Label(
            main,
            text="Tip: Browser mode works best for lazy-loaded or protected sites"
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 12))

        # Output directory
        save_lbl = ttk.Label(main, text="Save location", font=("Segoe UI", 11, "bold"))
        save_lbl.grid(row=3, column=0, sticky="w", pady=(0, 4))

        ttk.Entry(main, textvariable=self.output_var, width=78).grid(row=4, column=0, sticky="ew")
        ttk.Button(main, text="Browse", command=self.choose_folder).grid(row=4, column=1, padx=8)

        # Options
        opt = ttk.LabelFrame(main, text=" Options ", padding=12)
        opt.grid(row=5, column=0, columnspan=2, sticky="ew", pady=12)

        cb_browser = ttk.Checkbutton(
            opt,
            text="Use browser mode (Playwright - recommended)",
            variable=self.use_browser_var
        )
        cb_browser.pack(anchor="w")
        Tooltip(cb_browser, "Uses a real Chromium browser to bypass JS, lazy-load, and Cloudflare")

        ttk.Checkbutton(opt, text="Ignore GIF images", variable=self.exclude_gifs_var).pack(anchor="w")
        ttk.Checkbutton(
            opt,
            text="Skip very small images (<15 KB) to remove ads/logos",
            variable=self.skip_tiny_var
        ).pack(anchor="w")
        ttk.Checkbutton(
            opt,
            text="Aggressive ad/comment filtering",
            variable=self.aggressive_comments_var
        ).pack(anchor="w")

        ttk.Checkbutton(
            opt,
            text="Export as PDF",
            variable=self.generate_pdf_var,
            state="normal" if PIL_AVAILABLE else "disabled"
        ).pack(anchor="w")

        ttk.Checkbutton(
            opt,
            text="Export as EPUB",
            variable=self.generate_epub_var,
            state="normal" if EPUB_AVAILABLE and PIL_AVAILABLE else "disabled"
        ).pack(anchor="w")

        ttk.Checkbutton(
            opt,
            text="Export as CBZ (Comic Book ZIP)",
            variable=self.generate_cbz_var
        ).pack(anchor="w")

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)

        self.test_btn = ttk.Button(btn_frame, text="Test URL", command=self.test_url)
        self.test_btn.pack(side="left", padx=5)

        self.start_btn = ttk.Button(btn_frame, text="Start Download", command=self.start_download)
        self.start_btn.pack(side="left", padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", state="disabled", command=self.cancel)
        self.cancel_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="Open Folder", command=self.open_folder).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log).pack(side="left", padx=5)

        # Status & progress
        ttk.Label(main, textvariable=self.current_status, foreground="#0066cc").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(8, 4)
        )

        ttk.Label(main, text="Progress").grid(row=8, column=0, sticky="w", pady=(0, 4))
        prog_frame = ttk.Frame(main)
        prog_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.progress = ttk.Progressbar(prog_frame, mode="determinate", variable=self.progress_value)
        self.progress.pack(side="left", fill="x", expand=True)
        ttk.Label(prog_frame, textvariable=self.progress_label, width=6).pack(side="right", padx=4)

        # Log output
        ttk.Label(main, text="Log", font=("Segoe UI", 11, "bold")).grid(
            row=10, column=0, sticky="w", pady=(0, 4)
        )

        self.log = scrolledtext.ScrolledText(
            main,
            height=28,
            font=("Consolas", 10),
            bg="#fdfdfd",
            wrap="word"
        )
        self.log.grid(row=11, column=0, columnspan=2, sticky="nsew")

        self.log.tag_config("info", foreground="#333")
        self.log.tag_config("ok", foreground="#006400")
        self.log.tag_config("warn", foreground="#d35400")
        self.log.tag_config("error", foreground="#c0392b")

        main.columnconfigure(0, weight=1)
        main.rowconfigure(11, weight=1)

    def log_message(self, msg: str, tag: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{timestamp}] {msg}\n", tag)
        self.log.see(tk.END)
        self.root.update_idletasks()

    def update_status(self, text: str):
        self.current_status.set(text)
        self.root.update_idletasks()

    def clear_log(self):
        self.log.delete("1.0", tk.END)
        self.progress_value.set(0)
        self.progress_label.set("0%")
        self.update_status("Ready")

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_var.set(folder)

    def open_folder(self):
        path = Path(self.output_var.get().strip() or "~/Downloads/Comics").expanduser()
        path.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(path)
            elif "darwin" in os.name.lower():
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            self.log_message(f"Failed to open folder: {e}", "error")

    def cancel(self):
        self.running = False
        self.log_message("Cancel requested — stopping download...", "warn")

    def test_url(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Error", "Enter a URL first.")
            return
        threading.Thread(target=self._test_task, args=(url,), daemon=True).start()

    def _test_task(self, url):
        self.update_status("Testing...")
        self.start_btn["state"] = "disabled"
        self.test_btn["state"] = "disabled"
        try:
            html = self.fetch_page(url, self.use_browser_var.get())
            imgs = self.extract_image_urls(html, url)
            self.log_message(f"Test OK → found {len(imgs)} images", "ok")
            for i, img in enumerate(imgs[:10], 1):
                self.log_message(f"  {i:02d}  {img[:120]}...", "info")
            if len(imgs) > 10:
                self.log_message(f"  ... +{len(imgs)-10} more", "info")
        except Exception as e:
            self.log_message(f"Test failed: {str(e)[:180]}", "error")
        finally:
            self.start_btn["state"] = "normal"
            self.test_btn["state"] = "normal"
            self.update_status("Ready")

    def start_download(self):
        if self.running: return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Error", "Please enter a chapter URL.")
            return

        self.running = True
        self.start_btn["state"] = "disabled"
        self.test_btn["state"] = "disabled"
        self.cancel_btn["state"] = "normal"
        self.log.delete("1.0", tk.END)
        self.progress_value.set(0)
        self.progress_label.set("0%")
        self.update_status("Starting download...")

        threading.Thread(target=self.download_task, args=(url, self.output_var.get().strip()), daemon=True).start()

    def download_task(self, chapter_url: str, base_dir: str):
        saved_paths = []
        try:
            use_browser = self.use_browser_var.get() and PLAYWRIGHT_AVAILABLE
            self.update_status(f"Fetching page ({'Playwright' if use_browser else 'requests'})...")
            html = self.fetch_page(chapter_url, use_browser)

            self.update_status("Extracting image URLs...")
            image_urls = self.extract_image_urls(html, chapter_url)

            if not image_urls:
                self.log_message("No valid images found after filtering.", "error")
                return

            output_dir = self.get_output_directory(html, chapter_url, base_dir)
            self.log_message(f"Saving to: {output_dir}", "info")

            self.total_images = len(image_urls)
            self.log_message(f"Found {self.total_images} images.", "ok")

            output_dir.mkdir(parents=True, exist_ok=True)
            success = 0

            for i, img_url in enumerate(image_urls, 1):
                if not self.running:
                    break

                self.update_status(f"Downloading {i}/{self.total_images}...")
                filename = f"{i:03d}{Path(urlparse(img_url).path).suffix or '.jpg'}"
                save_path = output_dir / filename

                self.log_message(f"[{i:03d}/{self.total_images}] {filename}", "info")

                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": chapter_url,
                    }
                    r = requests.get(img_url, headers=headers, timeout=20, stream=True)
                    r.raise_for_status()

                    content = r.content
                    if self.skip_tiny_var.get() and len(content) < 15 * 1024:
                        self.log_message("  Skipped (too small)", "warn")
                        continue

                    with open(save_path, "wb") as f:
                        f.write(content)

                    success += 1
                    saved_paths.append(save_path)
                    perc = (i / self.total_images) * 100
                    self.progress_value.set(perc)
                    self.progress_label.set(f"{int(perc)}%")
                    time.sleep(0.25)

                except Exception as e:
                    self.log_message(f"  Failed: {str(e)[:100]}", "error")

            self.log_message(f"\nFinished → {success}/{self.total_images} images saved", "ok")
            self.log_message(f"→ {output_dir}", "ok")

            if self.generate_cbz_var.get():
                self.update_status("Creating CBZ...")
                self.generate_cbz(output_dir, saved_paths)

            if self.generate_pdf_var.get() and PIL_AVAILABLE:
                self.update_status("Generating PDF...")
                self.generate_pdf(output_dir)

            if self.generate_epub_var.get() and EPUB_AVAILABLE and PIL_AVAILABLE:
                self.update_status("Generating EPUB...")
                self.generate_epub(output_dir)

        except Exception as e:
            self.log_message(f"Critical error: {e}", "error")
        finally:
            self._finish()

    def fetch_page(self, url: str, use_browser: bool) -> str:
        if use_browser and PLAYWRIGHT_AVAILABLE:
            for attempt in range(1, 4):
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True, args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                        ])
                        context = browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            viewport={"width": 1280, "height": 900}
                        )
                        page = context.new_page()

                        try:
                            page.goto(url, wait_until="networkidle", timeout=50000)
                            page.wait_for_timeout(1800)

                            page.evaluate("""
                                () => {
                                    window.scrollTo(0, document.body.scrollHeight);
                                    document.querySelectorAll('img[data-src], img[data-lazy], img[data-lazy-src], img[data-original]').forEach(img => {
                                        if (img.dataset.src) img.src = img.dataset.src;
                                        if (img.dataset.lazy) img.src = img.dataset.lazy;
                                        if (img.dataset.lazySrc) img.src = img.dataset.lazySrc;
                                        if (img.dataset.original) img.src = img.dataset.original;
                                    });
                                }
                            """)

                            for _ in range(20):
                                page.evaluate("window.scrollBy(0, window.innerHeight * 0.75)")
                                page.wait_for_timeout(700)

                            html = page.content()
                            if len(html) < 4000:
                                raise ValueError("Page content suspiciously short")
                            return html
                        finally:
                            context.close()
                            browser.close()
                except Exception as e:
                    self.log_message(f"Playwright attempt {attempt}/3 failed: {str(e)[:140]}", "warn")
                    time.sleep(2.5)
            raise RuntimeError("Playwright failed after 3 attempts")

        # Fallback
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        r.raise_for_status()
        return r.text

    def extract_image_urls(self, html: str, base_url: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        candidates = set()

        selectors = [
            "#readerarea", ".reading-content", ".page-break", ".chapter-content", ".wt_viewer",
            "#chapter_area", ".manga-reader", "[aria-label*='Chapter']", ".read-container",
            "#chapter_boxImages", "#toon_img", ".image_story", ".imageChap", ".wp-manga-chapter-img",
            "figure[data-index]", ".img-responsive.image-chapter", ".mr-img"
        ]

        for sel in selectors:
            for cont in soup.select(sel):
                for img in cont.find_all("img"):
                    for src in self._get_img_sources(img, base_url):
                        candidates.add(src)

        if len(candidates) < 6:
            divs = soup.find_all(["div", "section", "article", "main"])
            best = max(divs, key=lambda d: len(d.find_all("img")), default=None)
            if best:
                for img in best.find_all("img"):
                    for src in self._get_img_sources(img, base_url):
                        candidates.add(src)

        if len(candidates) < 5:
            rx = re.findall(r'https?://[^\s"\'<>]+?\.(?:jpe?g|png|webp|avif|jpeg)(?:\?[^\s"\'<>]*)?', html, re.I)
            candidates.update(rx)

        filtered = []
        seen = set()
        for u in candidates:
            if u in seen: continue
            seen.add(u)
            if self._is_valid_image_url(u, base_url):
                filtered.append(u)

        def num_key(s):
            m = re.search(r'(\d+)(?:-\d+)?\.', s)
            return int(m.group(1)) if m else 999999
        filtered.sort(key=num_key)

        return filtered

    def _get_img_sources(self, img, base):
        attrs = ["src", "data-src", "data-lazy-src", "data-original", "data-lazy", "srcset"]
        srcs = []
        for a in attrs:
            v = img.get(a)
            if v:
                if a == "srcset":
                    v = v.split(",")[0].strip().split()[0]
                full = self.normalize_url(v, base)
                if full:
                    srcs.append(full)
        return srcs

    def normalize_url(self, src: str, base: str) -> str:
        src = (src or "").strip()
        if not src: return ""
        if src.startswith("//"): return "https:" + src
        if src.startswith("/"): return urljoin(base, src)
        if not src.startswith(("http://", "https://")): return urljoin(base, src)
        return src

    def _is_valid_image_url(self, url: str, chapter_url: str) -> bool:
        if not url.startswith(("http", "https")): return False
        low = url.lower()

        if self.exclude_gifs_var.get() and low.endswith(".gif"): return False

        junk = ["logo", "banner", "icon", "avatar", "thumb", "cover", "ad-", "advert", "emoji", "999.png", "discord"]
        if self.aggressive_comments_var.get():
            junk += ["comment", "disqus", "reply", "fb_", "social"]

        if any(k in low for k in junk): return False

        good = [".jpg", ".jpeg", ".png", ".webp", "cdn", "scans", "storage", "tnlycdn", "lastation", "manhwa", "toonily"]
        return any(x in low for x in good) or low.endswith((".jpg", ".jpeg", ".png", ".webp"))

    def get_output_directory(self, html: str, url: str, base_dir: str) -> Path:
        soup = BeautifulSoup(html, "html.parser")

        og_title = soup.find("meta", property="og:title")
        title = (og_title["content"] if og_title else soup.title.string or "").strip()

        if " - " in title:
            parts = [p.strip() for p in title.split(" - ")]
            comic = parts[0]
            chapter = " - ".join(parts[1:])
        elif "Chapter" in title or "Episode" in title:
            if "Chapter" in title:
                comic, chapter = title.split("Chapter", 1)
            else:
                comic, chapter = title.split("Episode", 1)
            comic = comic.strip()
            chapter = ("Chapter" if "Chapter" in title else "Episode") + chapter.strip()
        else:
            comic = "Unknown Comic"
            chapter = title or "Chapter"

        comic = re.sub(r'(Manhwa|Manga|Manhua|Read|Online|Latest).*', '', comic, flags=re.I).strip() or "Comic"
        chapter = re.sub(r'(Chapter|Episode|Ch\.?|Ep\.?)\s*', 'Ch. ', chapter, flags=re.I).strip() or "Chapter"

        return Path(base_dir) / self._sanitize(comic) / self._sanitize(chapter)

    def _sanitize(self, s: str) -> str:
        s = re.sub(r'[<>:"/\\|?*]', '', s)
        return re.sub(r'\s+', ' ', s).strip()[:85] or "Unknown"

    def generate_cbz(self, output_dir: Path, image_paths: list):
        try:
            cbz_path = output_dir / f"{output_dir.name}.cbz"
            with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for img_path in sorted(image_paths):
                    arcname = img_path.name
                    zf.write(img_path, arcname)
            self.log_message(f"CBZ archive created: {cbz_path}", "ok")
        except Exception as e:
            self.log_message(f"CBZ creation failed: {e}", "error")

    def generate_pdf(self, output_dir: Path):
        try:
            images = sorted(
                [p for p in output_dir.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')],
                key=lambda x: int(re.search(r'(\d+)', x.stem).group(1)) if re.search(r'(\d+)', x.stem) else 0
            )
            if not images:
                raise ValueError("No images found for PDF")

            imgs = [Image.open(p).convert("RGB") for p in images]
            pdf_path = output_dir / f"{output_dir.name}.pdf"
            imgs[0].save(pdf_path, "PDF", resolution=100.0, save_all=True, append_images=imgs[1:])
            self.log_message(f"PDF created: {pdf_path}", "ok")
        except Exception as e:
            self.log_message(f"PDF generation failed: {e}", "error")

    def generate_epub(self, output_dir: Path):
        try:
            book = epub.EpubBook()
            book.set_identifier(f"comic-{time.time()}")
            book.set_title(f"{output_dir.parent.name} - {output_dir.name}")
            book.add_author("Downloaded via Universal Comic Downloader")
            book.set_language('en')

            chapters = []
            images = sorted(
                [p for p in output_dir.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')],
                key=lambda x: int(re.search(r'(\d+)', x.stem).group(1)) if re.search(r'(\d+)', x.stem) else 0
            )

            for i, img_path in enumerate(images, 1):
                img_item = epub.EpubItem(
                    uid=f"image_{i}",
                    file_name=f"images/page_{i:03d}{img_path.suffix}",
                    media_type="image/jpeg" if img_path.suffix.lower() in ('.jpg', '.jpeg') else "image/png",
                    content=img_path.read_bytes()
                )
                book.add_item(img_item)

                chapter = epub.EpubHtml(title=f"Page {i}", file_name=f"page_{i:03d}.xhtml")
                chapter.content = f'<div><img src="{img_item.file_name}" style="max-width:100%;height:auto;" /></div>'
                book.add_item(chapter)
                chapters.append(chapter)

            book.toc = chapters
            book.spine = ['nav'] + chapters
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            epub_path = output_dir / f"{output_dir.name}.epub"
            epub.write_epub(str(epub_path), book)
            self.log_message(f"EPUB created: {epub_path}", "ok")
        except Exception as e:
            self.log_message(f"EPUB generation failed: {e}", "error")

    def _finish(self):
        self.running = False
        self.start_btn["state"] = "normal"
        self.test_btn["state"] = "normal"
        self.cancel_btn["state"] = "disabled"
        self.update_status("Ready")
        if self.total_images:
            self.progress_value.set(100)
            self.progress_label.set("100%")


if __name__ == "__main__":
    root = tk.Tk()
    app = download_comic(root)
    root.mainloop()
