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
import base64
import io

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
            pady=4,
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class UniversalComicDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Comic Downloader - Download any comic images.")
        self.root.geometry("950x700")
        self.root.resizable(True, True)

        self.bg_color = "#f0f4f8"
        self.accent_color = "#667eea"
        self.success_color = "#48bb78"
        self.warning_color = "#ed8936"
        self.error_color = "#f56565"

        self.root.configure(bg=self.bg_color)

        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.home() / "Downloads" / "Comics"))
        self.use_browser_var = tk.BooleanVar(value=PLAYWRIGHT_AVAILABLE)
        self.exclude_gifs_var = tk.BooleanVar(value=True)
        self.skip_tiny_var = tk.BooleanVar(value=True)
        self.aggressive_comments_var = tk.BooleanVar(value=True)
        self.convert_webp_var = tk.BooleanVar(value=False)
        self.convert_webp_cbz_var = tk.BooleanVar(value=True)
        self.generate_pdf_var = tk.BooleanVar(value=False)
        self.generate_epub_var = tk.BooleanVar(value=False)
        self.generate_cbz_var = tk.BooleanVar(value=True)

        self.running = False
        self.total_images = 0
        self._download_start = 0

        self.current_status = tk.StringVar(value="Ready to start")
        self.progress_value = tk.DoubleVar(value=0)
        self.progress_label = tk.StringVar(value="0%")
        self.current_step = tk.StringVar(value="")
        self.images_found = tk.StringVar(value="Images found: 0")
        self.images_downloaded = tk.StringVar(value="Downloaded: 0/0")

        self.setup_ui()

        self.log_message("=" * 60, "info")
        self.log_message("Comic Downloader - Download images from a url link", "ok")
        self.log_message("=" * 60, "info")

        if PLAYWRIGHT_AVAILABLE:
            self.log_message("✓ Browser mode locked and loaded", "ok")
        else:
            self.log_message(
                "⚠ Browser mode MIA - run: pip install playwright && playwright install",
                "warn",
            )

        if PIL_AVAILABLE:
            self.log_message("✓ Image wizardry enabled", "ok")
        else:
            self.log_message(
                "⚠ No Pillow, no PDF party (install: pip install pillow)", "warn"
            )

        if EPUB_AVAILABLE:
            self.log_message("✓ EPUB factory operational", "ok")
        else:
            self.log_message(
                "⚠ EPUB machine broke (install: pip install ebooklib)", "warn"
            )

        self.log_message("✓ CBZ archives always ready", "ok")
        self.log_message("-" * 60, "info")
        self.log_message("Drop a URL and download image", "info")
        self.log_message("", "info")

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Title.TLabel", font=("Segoe UI", 13, "bold"), foreground="#667eea"
        )
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9), foreground="#718096")
        style.configure(
            "Step.TLabel", font=("Segoe UI", 9, "bold"), foreground="#4a5568"
        )
        style.configure("Small.TLabel", font=("Segoe UI", 8), foreground="#666666")
        style.configure("TButton", font=("Segoe UI", 9), padding=(12, 6))
        style.configure(
            "Primary.TButton", font=("Segoe UI", 9, "bold"), padding=(12, 8)
        )

        main = ttk.Frame(self.root, padding="15")
        main.pack(fill=tk.BOTH, expand=True)

        # Row 0: Header
        header_frame = ttk.Frame(main)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(header_frame, text="Comic Downloader", style="Title.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Label(
            header_frame,
            text=" \u2022 Because manually downloading is for peasants",
            style="Subtitle.TLabel",
        ).pack(side=tk.LEFT, padx=(8, 0))

        # Row 1: URL + Save
        input_frame = ttk.Frame(main)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(input_frame, text="URL:", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Entry(input_frame, textvariable=self.url_var, font=("Segoe UI", 10)).pack(
            side=tk.LEFT, fill="x", expand=True, padx=(0, 10)
        )

        ttk.Label(input_frame, text="Save:", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Entry(
            input_frame, textvariable=self.output_var, font=("Segoe UI", 9), width=25
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            input_frame, text="Browse", command=self.choose_folder, width=8
        ).pack(side=tk.LEFT)

        # Row 2: Options
        opt_frame = ttk.Frame(main)
        opt_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        ttk.Checkbutton(opt_frame, text="Browser", variable=self.use_browser_var).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Checkbutton(
            opt_frame, text="WEBP\u2192JPG", variable=self.convert_webp_var
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(
            opt_frame, text="Skip GIF", variable=self.exclude_gifs_var
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(opt_frame, text="Skip Small", variable=self.skip_tiny_var).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Checkbutton(
            opt_frame, text="Filter", variable=self.aggressive_comments_var
        ).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Separator(opt_frame, orient="vertical").pack(side=tk.LEFT, fill="y", padx=8)

        ttk.Checkbutton(opt_frame, text="CBZ", variable=self.generate_cbz_var).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Checkbutton(
            opt_frame,
            text="WEBP\u2192JPG in CBZ",
            variable=self.convert_webp_cbz_var,
            state="normal" if PIL_AVAILABLE else "disabled",
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(
            opt_frame,
            text="PDF",
            variable=self.generate_pdf_var,
            state="normal" if PIL_AVAILABLE else "disabled",
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(
            opt_frame,
            text="EPUB",
            variable=self.generate_epub_var,
            state="normal" if EPUB_AVAILABLE and PIL_AVAILABLE else "disabled",
        ).pack(side=tk.LEFT)

        # Row 3: Action buttons
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        self.test_btn = ttk.Button(
            btn_frame, text="\U0001f50d Test", command=self.test_url, width=10
        )
        self.test_btn.pack(side=tk.LEFT, padx=(0, 6))
        self.start_btn = ttk.Button(
            btn_frame,
            text="\u25b6 Start",
            command=self.start_download,
            style="Primary.TButton",
            width=12,
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 6))
        self.cancel_btn = ttk.Button(
            btn_frame,
            text="\u23f9 Cancel",
            state="disabled",
            command=self.cancel,
            width=10,
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(
            btn_frame,
            text="\U0001f4c1 Folder",
            command=self.open_folder,
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            btn_frame, text="\U0001f5d1 Clear", command=self.clear_log, width=10
        ).pack(side=tk.LEFT)

        # Row 4: Progress bar + step text + stats
        progress_frame = ttk.Frame(main)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=(0, 6))

        self.step_label = ttk.Label(
            progress_frame, textvariable=self.current_step, style="Step.TLabel"
        )
        self.step_label.pack(anchor="w", pady=(0, 4))

        prog_row = ttk.Frame(progress_frame)
        prog_row.pack(fill="x", pady=(0, 4))
        self.progress = ttk.Progressbar(
            prog_row, mode="determinate", variable=self.progress_value
        )
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(
            prog_row,
            textvariable=self.progress_label,
            width=6,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

        stats_row = ttk.Frame(progress_frame)
        stats_row.pack(fill="x")
        ttk.Label(stats_row, textvariable=self.images_found, style="Small.TLabel").pack(
            side=tk.LEFT, padx=(0, 15)
        )
        ttk.Label(
            stats_row, textvariable=self.images_downloaded, style="Small.TLabel"
        ).pack(side=tk.LEFT)

        # Row 5: Activity log
        log_frame = ttk.Frame(main)
        log_frame.grid(row=5, column=0, sticky="nsew")

        self.log = scrolledtext.ScrolledText(
            log_frame,
            height=16,
            font=("Consolas", 9),
            bg="#ffffff",
            wrap="word",
            relief="flat",
            borderwidth=1,
        )
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("info", foreground="#4a5568")
        self.log.tag_config("ok", foreground="#48bb78")
        self.log.tag_config("warn", foreground="#ed8936")
        self.log.tag_config("error", foreground="#f56565")
        self.log.tag_config(
            "progress", foreground="#667eea", font=("Consolas", 9, "bold")
        )

        main.columnconfigure(0, weight=1)
        main.rowconfigure(5, weight=1)

    def log_message(self, msg: str, tag: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{timestamp}] {msg}\n", tag)
        self.log.see(tk.END)
        self.root.update_idletasks()

    def log_progress(self, current: int, total: int, label: str = ""):
        if total <= 0:
            return
        pct = current / total
        filled = int(pct * 20)
        bar = "\u2588" * filled + "\u2591" * (20 - filled)
        elapsed = time.time() - self._download_start if self._download_start else 0
        mins, secs = divmod(int(elapsed), 60)
        timestamp = time.strftime("%H:%M:%S")
        detail = f" \u2014 {mins:02d}:{secs:02d}" if elapsed > 0 else ""
        suffix = f" {label}" if label else ""
        line = f"[{timestamp}] [{bar}] {current}/{total}{suffix}{detail}\n"
        self.log.insert(tk.END, line, "progress")
        self.log.see(tk.END)
        self.root.update_idletasks()

    def update_status(self, text: str):
        self.current_status.set(text)
        self.root.update_idletasks()

    def clear_log(self):
        self.log.delete("1.0", tk.END)
        self.progress_value.set(0)
        self.progress_label.set("0%")
        self.current_step.set("")
        self.images_found.set("Images found: 0")
        self.images_downloaded.set("Downloaded: 0/0")
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
        self.update_status("Cancelling... (stopping after current image)")
        self.log_message(
            "Cancelling download - stopping after current image completes...", "warn"
        )

    def test_url(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Error", "Enter a URL first.")
            return
        threading.Thread(target=self._test_task, args=(url,), daemon=True).start()

    def _test_task(self, url):
        self.update_status("Testing URL...")
        self.start_btn["state"] = "disabled"
        self.test_btn["state"] = "disabled"
        try:
            self.log_message("Testing chapter URL...", "info")
            html = self.fetch_page(url, self.use_browser_var.get())
            imgs = self.extract_image_urls(html, url)

            self.log_message(f"✓ Test successful! Found {len(imgs)} images", "ok")
            self.images_found.set(f"Images found: {len(imgs)}")

            if imgs:
                self.log_message("First 10 images:", "info")
                for i, img in enumerate(imgs[:10], 1):
                    self.log_message(f"  {i:02d}. {img[:100]}...", "info")
                if len(imgs) > 10:
                    self.log_message(f"  ... and {len(imgs) - 10} more", "info")
                self.log_message(
                    "✓ Ready to download! Click 'Start Download' to begin.", "ok"
                )
        except Exception as e:
            self.log_message(f"✗ Test failed: {str(e)[:180]}", "error")
            self.log_message("Please check the URL and try again", "warn")
        finally:
            self.start_btn["state"] = "normal"
            self.test_btn["state"] = "normal"
            self.update_status("Ready")

    def start_download(self):
        if self.running:
            return
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
        self._download_start = time.time()
        self.update_status("Starting download...")

        threading.Thread(
            target=self.download_task,
            args=(url, self.output_var.get().strip()),
            daemon=True,
        ).start()

    def download_task(self, chapter_url: str, base_dir: str):
        saved_paths = []
        try:
            use_browser = self.use_browser_var.get() and PLAYWRIGHT_AVAILABLE

            self.current_step.set("Step 1/4: Fetching page...")
            self.update_status(
                f"Loading chapter page using {'Browser Mode' if use_browser else 'Direct Request'}..."
            )
            self.log_message(
                f"Method: {'Browser Mode (Playwright)' if use_browser else 'Direct HTTP Request'}",
                "info",
            )
            html = self.fetch_page(chapter_url, use_browser)
            self.log_message("✓ Page loaded successfully", "ok")

            self.current_step.set("Step 2/4: Finding images...")
            self.update_status("Analyzing page and extracting image URLs...")
            image_urls = self.extract_image_urls(html, chapter_url)

            if not image_urls:
                self.log_message(
                    "✗ Found absolutely nothing. This page is a ghost town.", "error"
                )
                if not use_browser:
                    self.log_message(
                        "Try enabling Browser Mode - maybe that'll help", "warn"
                    )
                return

            output_dir = self.get_output_directory(html, chapter_url, base_dir)
            self.log_message(f"Save location: {output_dir}", "info")

            self.total_images = len(image_urls)
            self.images_found.set(f"Images found: {self.total_images}")
            self.log_message(f"✓ Found {self.total_images} images to download", "ok")

            output_dir.mkdir(parents=True, exist_ok=True)
            questionable_dir = output_dir / "_questionable_images"
            success = 0

            self.current_step.set("Step 3/4: Downloading images...")

            browser_urls = []
            if use_browser and PLAYWRIGHT_AVAILABLE:
                self.log_message("Attempting batch download with browser...", "info")
                self.update_status("Using browser to capture all images at once...")
                browser_urls = self.batch_download_with_browser(chapter_url, image_urls)
                if browser_urls:
                    self.log_message(
                        f"✓ Successfully captured {len(browser_urls)} images from browser",
                        "ok",
                    )

            # If browser found more images than HTML parsing (virtualized SPA),
            # merge the extras into image_urls so we download everything.
            # browser_urls is already in page order from network interception.
            if browser_urls and len(browser_urls) > len(image_urls):
                extra_urls = [u for u in browser_urls if u not in image_urls]
                if extra_urls:
                    image_urls = list(image_urls) + extra_urls
                    self.log_message(
                        f"Browser found {len(extra_urls)} additional images, total now: {len(image_urls)}",
                        "info",
                    )
                    self.total_images = len(image_urls)
                    self.images_found.set(f"Images found: {self.total_images}")

            for i, img_url in enumerate(image_urls, 1):
                if not self.running:
                    self.log_message("", "info")
                    self.log_message("=" * 60, "warn")
                    self.log_message(
                        f"✗ Cancelled: User said 'nah I'm good' - Saved {success}/{self.total_images} images",
                        "warn",
                    )
                    self.log_message("=" * 60, "warn")
                    break

                self.update_status(f"Downloading image {i} of {self.total_images}...")
                self.images_downloaded.set(f"Downloaded: {success}/{self.total_images}")
                filename = f"{i:03d}{Path(urlparse(img_url).path).suffix or '.jpg'}"
                save_path = output_dir / filename

                self.log_message(f"[{i:03d}/{self.total_images}] {filename}", "info")
                self.log_message(f"  {img_url}", "info")

                if not self.running:
                    self.log_message("  ✗ Cancelled", "warn")
                    break

                try:
                    if not self.running:
                        break

                    content = None

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": chapter_url,
                        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        "Sec-Ch-Ua-Mobile": "?0",
                        "Sec-Ch-Ua-Platform": '"Windows"',
                        "Sec-Fetch-Dest": "image",
                        "Sec-Fetch-Mode": "no-cors",
                        "Sec-Fetch-Site": "cross-site",
                    }

                    try:
                        r = requests.get(
                            img_url,
                            headers=headers,
                            timeout=20,
                            stream=True,
                            allow_redirects=True,
                        )
                        r.raise_for_status()
                        content = r.content
                        size_kb = len(content) // 1024
                        self.log_message(f"  Size: {size_kb} KB", "info")
                    except requests.exceptions.HTTPError as e:
                        if "403" in str(e) and use_browser and PLAYWRIGHT_AVAILABLE:
                            self.log_message(
                                "  Got 403'd, trying browser mode...", "warn"
                            )
                            content = self.download_image_with_browser(
                                img_url, chapter_url
                            )
                            if content:
                                size_kb = len(content) // 1024
                                self.log_message(f"  Size: {size_kb} KB", "info")
                        else:
                            raise

                    if content is None:
                        raise ValueError("Image download returned nothing, L")

                    if len(content) < 50 * 1024:
                        is_suspicious = False

                        if len(content) < 15 * 1024:
                            is_suspicious = True
                        elif len(content) < 50 * 1024:
                            if filename.lower().endswith(".png") and PIL_AVAILABLE:
                                try:
                                    from PIL import Image as PILImage

                                    img = PILImage.open(io.BytesIO(content))
                                    width, height = img.size

                                    if width < 200 or height < 200:
                                        is_suspicious = True
                                    elif width / height > 8 or height / width > 8:
                                        is_suspicious = True
                                except:
                                    is_suspicious = True

                        if is_suspicious:
                            if self.skip_tiny_var.get():
                                self.log_message(
                                    "  ⚠ Skipped (sus smol boi - probably emoji/icon)",
                                    "warn",
                                )
                                continue
                            else:
                                questionable_dir.mkdir(parents=True, exist_ok=True)
                                questionable_path = questionable_dir / filename
                                with open(questionable_path, "wb") as f:
                                    f.write(content)
                                self.log_message(
                                    f"  ⚠ Quarantined to _questionable_images ({len(content) // 1024} KB)",
                                    "warn",
                                )
                                continue

                    if self.convert_webp_var.get() and PIL_AVAILABLE:
                        if filename.lower().endswith((".webp", ".png")):
                            try:
                                from PIL import Image as PILImage

                                img = PILImage.open(io.BytesIO(content))

                                if img.mode in ("RGBA", "LA", "P"):
                                    background = PILImage.new(
                                        "RGB", img.size, (255, 255, 255)
                                    )
                                    if img.mode == "P":
                                        img = img.convert("RGBA")
                                    background.paste(
                                        img,
                                        mask=img.split()[-1]
                                        if img.mode == "RGBA"
                                        else None,
                                    )
                                    img = background
                                elif img.mode != "RGB":
                                    img = img.convert("RGB")

                                jpg_path = save_path.with_suffix(".jpg")
                                img.save(jpg_path, "JPEG", quality=95, optimize=True)

                                save_path = jpg_path
                                filename = jpg_path.name
                                self.log_message(
                                    f"  ✓ Converted to JPG ({len(content) // 1024} KB → {jpg_path.stat().st_size // 1024} KB)",
                                    "ok",
                                )
                            except Exception as e:
                                with open(save_path, "wb") as f:
                                    f.write(content)
                                self.log_message(
                                    f"  ⚠ Conversion failed ({str(e)[:50]}), saved anyway",
                                    "warn",
                                )
                        else:
                            with open(save_path, "wb") as f:
                                f.write(content)
                    else:
                        with open(save_path, "wb") as f:
                            f.write(content)

                    success += 1
                    saved_paths.append(save_path)
                    self.images_downloaded.set(
                        f"Downloaded: {success}/{self.total_images}"
                    )
                    perc = (i / self.total_images) * 100
                    self.progress_value.set(perc)
                    self.progress_label.set(f"{int(perc)}%")
                    self.log_message(f"  ✓ Saved", "ok")

                    time.sleep(0.05)

                except Exception as e:
                    self.log_message(f"  ✗ Failed: {str(e)[:100]}", "error")

            if self.running:
                self.log_message("", "info")
                self.log_message("=" * 60, "info")
                self.log_message(
                    f"✓ All done! Successfully yoinked {success}/{self.total_images} images",
                    "ok",
                )
                self.log_message(f"Location: {output_dir}", "info")
                self.log_message("=" * 60, "info")
            else:
                pass

            exports_created = []
            if self.running and self.generate_cbz_var.get():
                self.current_step.set("Step 4/4: Creating CBZ file...")
                self.update_status("Generating CBZ archive...")
                if self.generate_cbz(output_dir, saved_paths):
                    exports_created.append("CBZ")

            if self.running and self.generate_pdf_var.get() and PIL_AVAILABLE:
                self.current_step.set("Step 4/4: Creating PDF file...")
                self.update_status("Generating PDF document...")
                if self.generate_pdf(output_dir):
                    exports_created.append("PDF")

            if (
                self.running
                and self.generate_epub_var.get()
                and EPUB_AVAILABLE
                and PIL_AVAILABLE
            ):
                self.current_step.set("Step 4/4: Creating EPUB file...")
                self.update_status("Generating EPUB ebook...")
                if self.generate_epub(output_dir):
                    exports_created.append("EPUB")

            if exports_created:
                self.log_message(
                    f"✓ Generated formats: {', '.join(exports_created)}", "ok"
                )

            self.current_step.set("Complete!")
            self.update_status("All done! Ready for next download")

        except Exception as e:
            self.log_message(f"Everything exploded: {e}", "error")
        finally:
            self._finish()

    def batch_download_with_browser(self, chapter_url: str, image_urls: list) -> list:
        if not PLAYWRIGHT_AVAILABLE:
            return []

        try:
            self.log_message("Launching sneaky browser...", "info")
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ],
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    ignore_https_errors=True,
                )

                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                page = context.new_page()

                # Set up network interception BEFORE navigation to catch ALL image responses
                intercepted_images = {}

                def _on_response(response):
                    try:
                        url = response.url
                        if response.status == 200 and len(url) > 20:
                            ct = response.headers.get("content-type", "")
                            if "image" in ct:
                                body = response.body()
                                if body and len(body) > 1000:
                                    intercepted_images[url] = body
                    except:
                        pass

                page.on("response", _on_response)

                self.log_message("Loading page...", "info")
                page.goto(chapter_url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(5000)

                has_virtualization = page.evaluate("""
                    () => {
                        return document.querySelectorAll('[data-page]').length > 10 ||
                               document.querySelectorAll('.rpage-page').length > 0;
                    }
                """)

                images_data = {}

                if has_virtualization:
                    self.log_message(
                        "Detected virtualized SPA - using network interception to capture all images...",
                        "info",
                    )

                    # Find the actual scroll container (comix.to uses .rpage-main, not window)
                    scroll_container_js = page.evaluate("""
                        () => {
                            const main = document.querySelector('.rpage-main');
                            if (main && (main.scrollHeight > main.clientHeight || getComputedStyle(main).overflow !== 'visible')) {
                                return '.rpage-main';
                            }
                            const inner = document.querySelector('.rpage-main__inner');
                            if (inner && inner.scrollHeight > inner.clientHeight) {
                                return '.rpage-main__inner';
                            }
                            return null;
                        }
                    """)
                    self.log_message(
                        f"  Scroll container: {scroll_container_js or 'window'}", "info"
                    )

                    # Get total page count from [data-page] attributes (scoped to reader container only)
                    container_selector = scroll_container_js or ".rpage-main"
                    page_info = page.evaluate(f"""
                        () => {{
                            const container = document.querySelector('{container_selector}') || document;
                            const pages = container.querySelectorAll('.rpage-page[data-page]');
                            const nums = [];
                            for (const p of pages) {{
                                const n = parseInt(p.getAttribute('data-page'));
                                if (!isNaN(n)) nums.push(n);
                            }}
                            nums.sort((a, b) => a - b);
                            return nums;
                        }}
                    """)

                    if page_info:
                        total_pages = len(page_info)
                        self.log_message(
                            f"  Found {total_pages} pages in reader container (data-page attributes), scrolling to each...",
                            "info",
                        )

                        url_to_page = {}

                        for idx, page_num in enumerate(page_info):
                            if not self.running:
                                break

                            # Scroll the specific page element into view to trigger image load
                            page.evaluate(f"""
                                () => {{
                                    const container = document.querySelector('{container_selector}') || document;
                                    const el = container.querySelector('.rpage-page[data-page="{page_num}"]');
                                    if (el) el.scrollIntoView({{behavior: 'instant', block: 'center'}});
                                }}
                            """)

                            page.wait_for_timeout(500)

                            # Trigger lazy load AND record the image URL immediately (fresh, not virtualized)
                            page_src = page.evaluate(f"""
                                () => {{
                                    const container = document.querySelector('{container_selector}') || document;
                                    const el = container.querySelector('.rpage-page[data-page="{page_num}"]');
                                    if (!el) return null;
                                    const img = el.querySelector('img.rpage-page__img');
                                    if (!img) return null;
                                    if (img.dataset && img.dataset.src && (!img.src || img.src.includes('data:'))) {{
                                        img.src = img.dataset.src;
                                    }}
                                    return img.src && !img.src.includes('data:') ? img.src : null;
                                }}
                            """)

                            page.wait_for_timeout(300)

                            if page_src:
                                url_to_page[page_src] = page_num

                            if (idx + 1) % 10 == 0 or idx + 1 == total_pages:
                                self.log_message(
                                    f"  Scrolled to page {idx + 1}/{total_pages}, intercepted {len(intercepted_images)} images...",
                                    "info",
                                )

                        # Wait a bit for any remaining in-flight requests
                        page.wait_for_timeout(2000)

                        # Filter intercepted images to only comic CDN images, strip query params & deduplicate
                        comic_cdn_domains = {"wowpic4.store", "wowpic", "ek10"}
                        filtered_by_domain = {}
                        for url, body in intercepted_images.items():
                            domain = urlparse(url).netloc
                            if any(d in domain for d in comic_cdn_domains):
                                base_url = urljoin(url, urlparse(url).path)
                                if base_url not in filtered_by_domain:
                                    filtered_by_domain[base_url] = body

                        # Also match base URLs (without query params) for url_to_page
                        url_to_page_normalized = {}
                        for url, page_num in url_to_page.items():
                            url_to_page_normalized[url] = page_num
                            base_url = urljoin(url, urlparse(url).path)
                            if base_url != url:
                                url_to_page_normalized[base_url] = page_num

                        # Sort filtered images by their data-page number
                        sorted_urls = sorted(
                            filtered_by_domain.keys(),
                            key=lambda u: url_to_page_normalized.get(u, 999999),
                        )

                        # Only keep URLs that have a page mapping (excludes thumbnails, related chapters, etc.)
                        mapped_urls = [
                            u
                            for u in sorted_urls
                            if url_to_page_normalized.get(u, 999999) <= total_pages
                        ]
                        unmapped_count = len(sorted_urls) - len(mapped_urls)
                        if unmapped_count:
                            self.log_message(
                                f"  Skipped {unmapped_count} unmapped CDN images (thumbnails, related chapters, etc.)",
                                "info",
                            )

                        # Convert intercepted network responses to base64 for images_data (in page order)
                        for url in mapped_urls:
                            body = filtered_by_domain[url]
                            images_data[url] = base64.b64encode(body).decode("ascii")

                        self.log_message(
                            f"  Network interception captured {len(images_data)} unique images",
                            "ok",
                        )

                        # If network interception didn't get everything, fall back to
                        # DOM scanning + fetch for whatever is currently visible
                        if len(images_data) < total_pages:
                            self.log_message(
                                f"  Network got {len(images_data)}/{total_pages}, supplementing with DOM scan...",
                                "info",
                            )
                            # Scroll back to top and do a full pass
                            if scroll_container_js:
                                page.evaluate(f"""
                                    () => {{
                                        const el = document.querySelector('{scroll_container_js}');
                                        if (el) el.scrollTop = 0;
                                    }}
                                """)
                            else:
                                page.evaluate("window.scrollTo(0, 0)")
                            page.wait_for_timeout(1000)

                            for idx, page_num in enumerate(page_info):
                                if not self.running:
                                    break
                                if len(images_data) >= total_pages:
                                    break

                                page.evaluate(f"""
                                    () => {{
                                        const container = document.querySelector('{container_selector}') || document;
                                        const el = container.querySelector('.rpage-page[data-page="{page_num}"]');
                                        if (el) el.scrollIntoView({{behavior: 'instant', block: 'center'}});
                                    }}
                                """)
                                page.wait_for_timeout(400)

                                # Grab whatever img src is currently in the DOM for this page
                                dom_scan_js = f"""
                                    const container = document.querySelector('{container_selector}') || document;
                                    const imgs = container.querySelectorAll('.rpage-page__img');
                                    for (const img of imgs) {{
                                        const src = img.src || img.dataset.src;
                                        if (!src || src.includes('data:image') || existingKeys.includes(src)) continue;
                                        if (img.tagName === 'CANVAS') continue;
                                        if (!img.complete || !img.naturalWidth) continue;
                                        results[src] = true;
                                    }}
                                """
                                new_urls = page.evaluate(
                                    """(existingKeys) => {
                                        const results = {};
                                        """
                                    + dom_scan_js
                                    + """
                                        return Object.keys(results);
                                    }
                                """,
                                    list(images_data.keys()),
                                )

                                for img_url in new_urls:
                                    if img_url in images_data:
                                        continue
                                    try:
                                        b64 = page.evaluate(
                                            """
                                            async (url) => {
                                                try {
                                                    const resp = await fetch(url, {mode: 'cors'});
                                                    const buf = await resp.arrayBuffer();
                                                    const bytes = new Uint8Array(buf);
                                                    let binary = '';
                                                    for (let i = 0; i < bytes.length; i++) {
                                                        binary += String.fromCharCode(bytes[i]);
                                                    }
                                                    return btoa(binary);
                                                } catch(e) {
                                                    return null;
                                                }
                                            }
                                        """,
                                            img_url,
                                        )
                                        if b64 and len(b64) > 100:
                                            images_data[img_url] = b64
                                    except:
                                        pass

                            self.log_message(
                                f"  After DOM supplement: {len(images_data)} images total",
                                "ok",
                            )
                    else:
                        # Fallback: pixel-based scrolling if no data-page attributes found
                        self.log_message(
                            "  No data-page attributes found, falling back to pixel scroll...",
                            "info",
                        )
                        scroll_pos = 0
                        scroll_step = 1500
                        stale_count = 0
                        total_est = len(image_urls) if image_urls else 150

                        for target_page in range(0, total_est + 1):
                            if not self.running:
                                break

                            if scroll_container_js:
                                page.evaluate(f"""
                                    () => {{
                                        const el = document.querySelector('{scroll_container_js}');
                                        if (el) el.scrollTop = {scroll_pos};
                                    }}
                                """)
                            else:
                                page.evaluate(f"window.scrollTo(0, {scroll_pos})")

                            page.wait_for_timeout(400)

                            batch = page.evaluate(
                                """
                                (existingKeys) => {
                                    const results = {};
                                    const imgs = document.querySelectorAll('.rpage-page__img');
                                    for (const img of imgs) {
                                        const src = img.src || img.dataset.src;
                                        if (!src || src.includes('data:image') || existingKeys.includes(src)) continue;
                                        if (img.tagName === 'CANVAS') continue;
                                        if (!img.complete || !img.naturalWidth) continue;
                                        results[src] = 'pending_fetch';
                                    }
                                    return results;
                                }
                            """,
                                list(images_data.keys()),
                            )

                            for img_url in batch:
                                if img_url in images_data:
                                    continue
                                try:
                                    b64 = page.evaluate(
                                        """
                                        async (url) => {
                                            try {
                                                const resp = await fetch(url, {mode: 'cors'});
                                                const buf = await resp.arrayBuffer();
                                                const bytes = new Uint8Array(buf);
                                                let binary = '';
                                                for (let i = 0; i < bytes.length; i++) {
                                                    binary += String.fromCharCode(bytes[i]);
                                                }
                                                return btoa(binary);
                                            } catch(e) {
                                                return null;
                                            }
                                        }
                                    """,
                                        img_url,
                                    )
                                    if b64 and len(b64) > 100:
                                        images_data[img_url] = b64
                                except:
                                    pass

                            new_count = len(images_data)
                            if target_page % 10 == 0:
                                self.log_message(
                                    f"  Captured {new_count} images so far (scroll ~{scroll_pos}px)...",
                                    "info",
                                )

                            if new_count > 0 and new_count == stale_count:
                                stale_count += 1
                                if stale_count > 15:
                                    self.log_message(
                                        "  No new images for a while, stopping scroll...",
                                        "info",
                                    )
                                    break
                            else:
                                stale_count = 0

                            scroll_pos += scroll_step

                else:
                    self.log_message(
                        "Scrolling like a madman to trigger lazy images...", "info"
                    )
                    page_height = page.evaluate("document.body.scrollHeight")
                    viewport_height = page.evaluate("window.innerHeight")

                    scroll_steps = max(20, int(page_height / viewport_height) + 5)
                    for i in range(scroll_steps):
                        page.evaluate(
                            f"window.scrollTo(0, {i * viewport_height * 0.8})"
                        )
                        page.wait_for_timeout(400)

                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(3000)

                    # Final grab for non-SPA: fetch-based to avoid CORS canvas taint
                    self.log_message("Ripping images from browser memory...", "info")
                    all_urls = page.evaluate("""
                        () => {
                            const urls = [];
                            const images = document.querySelectorAll('img');
                            for (const img of images) {
                                const src = img.src || img.dataset.src || img.dataset.lazySrc;
                                if (!src || src.includes('data:image') || src.includes('1x1')) continue;
                                if (!img.complete || !img.naturalWidth || !img.naturalHeight) continue;
                                urls.push(src);
                            }
                            return urls;
                        }
                    """)
                    for img_url in all_urls:
                        if img_url in images_data:
                            continue
                        try:
                            b64 = page.evaluate(
                                """
                                async (url) => {
                                    try {
                                        const resp = await fetch(url, {mode: 'cors'});
                                        const buf = await resp.arrayBuffer();
                                        const bytes = new Uint8Array(buf);
                                        let binary = '';
                                        for (let i = 0; i < bytes.length; i++) {
                                            binary += String.fromCharCode(bytes[i]);
                                        }
                                        return btoa(binary);
                                    } catch(e) {
                                        return null;
                                    }
                                }
                            """,
                                img_url,
                            )
                            if b64 and len(b64) > 100:
                                images_data[img_url] = b64
                        except:
                            pass

                context.close()
                browser.close()

                return list(images_data.keys())

        except Exception as e:
            self.log_message(f"Browser batch download failed: {str(e)[:100]}", "warn")
            return []

    def download_image_with_browser(self, img_url: str, referer_url: str) -> bytes:
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed, can't browser mode this")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                    ],
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    extra_http_headers={
                        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    ignore_https_errors=True,
                )

                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                page = context.new_page()

                try:
                    page.goto(referer_url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(2000)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)
                except Exception as e:
                    self.log_message(f"    Page threw a tantrum: {str(e)[:50]}", "warn")

                try:
                    img_selector = f'img[src="{img_url}"], img[data-src="{img_url}"]'
                    if page.locator(img_selector).count() > 0:
                        img_data = page.evaluate(f'''
                            async () => {{
                                const img = document.querySelector('img[src="{img_url}"], img[data-src="{img_url}"]');
                                if (!img) return null;
                                const canvas = document.createElement('canvas');
                                canvas.width = img.naturalWidth;
                                canvas.height = img.naturalHeight;
                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(img, 0, 0);
                                return canvas.toDataURL('image/webp').split(',')[1];
                            }}
                        ''')

                        if img_data:
                            content = base64.b64decode(img_data)
                            context.close()
                            browser.close()
                            return content
                except:
                    pass

                response = page.goto(
                    img_url, wait_until="domcontentloaded", timeout=20000
                )
                if response and response.ok:
                    content = response.body()
                    context.close()
                    browser.close()
                    return content
                else:
                    context.close()
                    browser.close()
                    raise ValueError(
                        f"Download failed with status {response.status if response else 'unknown'}"
                    )

        except Exception as e:
            raise RuntimeError(f"Browser download error: {str(e)}")

    def fetch_page(self, url: str, use_browser: bool) -> str:
        domain = urlparse(url).netloc.lower()
        if "rawkuma.net" in domain:
            self.log_message(
                f"{domain} detected, using direct HTTP fetch instead of browser.",
                "info",
            )
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            r.raise_for_status()
            return r.text

        if use_browser and PLAYWRIGHT_AVAILABLE:
            for attempt in range(1, 4):
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(
                            headless=True,
                            args=[
                                "--disable-blink-features=AutomationControlled",
                                "--no-sandbox",
                            ],
                        )
                        context = browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            viewport={"width": 1280, "height": 900},
                        )
                        page = context.new_page()

                        def safe_eval(script, *args):
                            try:
                                if args:
                                    return page.evaluate(script, *args)
                                return page.evaluate(script)
                            except Exception as e:
                                self.log_message(
                                    f"  Browser evaluate failed: {str(e)[:120]}",
                                    "warn",
                                )
                                return None

                        try:
                            is_spa = any(
                                d in domain for d in ["comix.to", "cocomic.co"]
                            )
                            is_mangaball = "mangaball.net" in domain

                            if is_spa or is_mangaball:
                                self.log_message(
                                    f"{domain} detected - using networkidle...",
                                    "info",
                                )
                                page.goto(url, wait_until="networkidle", timeout=90000)
                            else:
                                self.log_message(
                                    f"Navigating to {domain} using domcontentloaded...",
                                    "info",
                                )
                                page.goto(
                                    url, wait_until="domcontentloaded", timeout=60000
                                )

                            try:
                                page.wait_for_load_state(
                                    "networkidle" if is_spa or is_mangaball else "domcontentloaded",
                                    timeout=15000,
                                )
                            except Exception:
                                pass

                            if is_mangaball:
                                try:
                                    page.wait_for_selector("#mangaPages, .manga-pages", timeout=60000)
                                except Exception:
                                    self.log_message(
                                        "mangaball.net selector did not appear before timeout.",
                                        "warn",
                                    )

                            page.wait_for_timeout(2500)

                            lazy_images_js = """
                                () => {
                                    document.querySelectorAll('img[data-src], img[data-lazy], img[data-lazy-src], img[data-original]').forEach(img => {
                                        if (img.dataset.src) img.src = img.dataset.src;
                                        if (img.dataset.lazy) img.src = img.dataset.lazy;
                                        if (img.dataset.lazySrc) img.src = img.dataset.lazySrc;
                                        if (img.dataset.original) img.src = img.dataset.original;
                                    });
                                }
                            """
                            safe_eval(lazy_images_js)

                            if is_spa:
                                scroll_container = safe_eval("""
                                    () => {
                                        const main = document.querySelector('.rpage-main');
                                        if (main && (main.scrollHeight > main.clientHeight || getComputedStyle(main).overflow !== 'visible')) {
                                            return '.rpage-main';
                                        }
                                        const inner = document.querySelector('.rpage-main__inner');
                                        if (inner && inner.scrollHeight > inner.clientHeight) {
                                            return '.rpage-main__inner';
                                        }
                                        return null;
                                    }
                                """)
                                self.log_message(
                                    f"  SPA scroll container: {scroll_container or 'window'}",
                                    "info",
                                )

                                scroll_pos = 0
                                scroll_step = 2000
                                while True:
                                    if scroll_container:
                                        safe_eval(f"""
                                            () => {{
                                                const el = document.querySelector('{scroll_container}');
                                                if (el) el.scrollTop = {scroll_pos};
                                            }}
                                        """)
                                    else:
                                        safe_eval(f"window.scrollTo(0, {scroll_pos})")
                                    page.wait_for_timeout(300)
                                    at_bottom = safe_eval(f"""
                                        () => {{
                                            const el = {scroll_container and f"document.querySelector('{scroll_container}')" or "window"};
                                            const scrollTop = el === window ? window.scrollY : el.scrollTop;
                                            const scrollHeight = el === window ? document.body.scrollHeight : el.scrollHeight;
                                            const clientHeight = el === window ? window.innerHeight : el.clientHeight;
                                            return (scrollTop + clientHeight) >= scrollHeight - 100;
                                        }}
                                    """)
                                    if at_bottom and scroll_pos > 2000:
                                        break
                                    scroll_pos += scroll_step
                                page.wait_for_timeout(2000)
                            else:
                                page_height = safe_eval("document.body.scrollHeight") or 0
                                viewport_height = safe_eval("window.innerHeight") or 1080
                                scroll_steps = max(
                                    25, int(page_height / viewport_height) + 5
                                )

                                for i in range(scroll_steps):
                                    safe_eval(
                                        f"window.scrollTo(0, {i * viewport_height * 0.75})"
                                    )
                                    page.wait_for_timeout(500)

                            safe_eval("window.scrollTo(0, document.body.scrollHeight)")
                            page.wait_for_timeout(2000)
                            safe_eval("window.scrollTo(0, 0)")
                            page.wait_for_timeout(1000)

                            html = page.content()
                            if len(html) < 4000:
                                raise ValueError("Sus page, too short")
                            return html
                        finally:
                            try:
                                context.close()
                            except Exception:
                                pass
                            try:
                                browser.close()
                            except Exception:
                                pass
                except Exception as e:
                    self.log_message(
                        f"Browser attempt {attempt}/3 failed: {str(e)[:100]}", "warn"
                    )
                    time.sleep(2.5)
            raise RuntimeError("Browser gave up after 3 tries, site too stronk")

        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        r.raise_for_status()
        return r.text

    def extract_image_urls(self, html: str, base_url: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        candidates = set()

        domain = urlparse(base_url).netloc.lower()
        self.log_message(f"Scraping: {domain}", "info")
        if "mangaball.net" in domain:
            self.log_message(
                "mangaball.net support is currently broken/WIP. The downloader will skip special mangaball extraction.",
                "warn",
            )

        def num_key(s):
            patterns = [
                r"ch[_-]?\d+[_-](\d+)",
                r"/(\d+)\.(?:jpg|jpeg|png|webp)",
                r"page[_-]?(\d+)",
                r"c_\d+_(\d+)",
                r"(\d+)(?:-\d+)?\.(?:jpg|jpeg|png|webp)",
            ]
            for pattern in patterns:
                m = re.search(pattern, s.lower())
                if m:
                    return int(m.group(1))
            return 999999  # idk

        # rawkuma.net: extract images from the reader section and CDN src patterns
        if "rawkuma.net" in domain:
            rawkuma_imgs = soup.select(
                "section[data-image-data] img, img[src*='rcdn.kyut.dev']"
            )
            if rawkuma_imgs:
                for img in rawkuma_imgs:
                    for src in self._get_img_sources(img, base_url):
                        if src:
                            candidates.add(src)
                if candidates:
                    ordered = sorted(candidates, key=num_key)
                    self.log_message(
                        f"rawkuma.net: extracted {len(ordered)} images from reader HTML",
                        "ok",
                    )
                    return ordered

        # mangaball.net support is currently disabled and is in WIP .
        # if "mangaball.net" in domain:
        #     page_items = soup.select("#mangaPages .manga-page[data-page]")
        #     ordered = []
        #     if page_items:
        #         def page_num(el):
        #             try:
        #                 return int(el.get("data-page", "999999"))
        #             except (ValueError, TypeError):
        #                 return 999999

        #         page_items.sort(key=page_num)
        #         for page_item in page_items:
        #             img = page_item.select_one("img")
        #             if img:
        #                 for src in self._get_img_sources(img, base_url):
        #                     if src:
        #                         ordered.append(src)

        #     if not ordered:
        #         alt_imgs = soup.select("#mangaPages img, .manga-pages img, img.manga-image")
        #         for img in alt_imgs:
        #             for src in self._get_img_sources(img, base_url):
        #                 if src:
        #                     ordered.append(src)

        #     ordered = [u for u in ordered if u]
        #     if ordered:
        #         ordered = sorted(ordered, key=num_key)
        #         self.log_message(
        #             f"mangaball.net: extracted {len(ordered)} page images sorted for download",
        #             "ok",
        #         )
        #         self.log_message(
        #             f"Got {len(ordered)} clean images ready to download", "ok"
        #         )
        #         return ordered

        # comix.to: extract ONLY from rpage-page__img, sorted by data-page number
        if "comix.to" in domain:
            pages = soup.select(".rpage-page[data-page]")
            if pages:

                def page_num(el):
                    try:
                        return int(el.get("data-page", "999999"))
                    except (ValueError, TypeError):
                        return 999999

                pages.sort(key=page_num)
                ordered = []
                for p in pages:
                    img = p.select_one("img.rpage-page__img")
                    if img:
                        for src in self._get_img_sources(img, base_url):
                            if src and "wowpic" in src:
                                ordered.append(src)
                if ordered:
                    self.log_message(
                        f"comix.to: extracted {len(ordered)} page images sorted by data-page",
                        "ok",
                    )
                    self.log_message(
                        f"Got {len(ordered)} clean images ready to download", "ok"
                    )
                    return ordered

        selectors = [
            # Comix.to (React SPA)
            "img.rpage-page__img",
            ".rpage-page img",
            ".rpage-main img",
            # Cocomic.co / Madara theme
            ".reading-content img.wp-manga-chapter-img",
            ".entry-content img.wp-manga-chapter-img",
            ".page-break img.wp-manga-chapter-img",
            ".reading-content .page-break img",
            # FlameComics
            ".mantine-Stack-root img[alt*='Chapter']",
            ".m_6d731127 img",
            # MangaBall
            "img.manga-image",
            "img.lazy-load",
            "img.lazy-loaded",
            # KuraManga
            ".container img[alt*='Chapter']",
            # LuaComic
            ".container .flex img.lazy",
            ".container .flex img",
            # uhhh just patterns
            "section[aria-label*='Chapter'] img.lazy-image",
            "figure[data-index] img.mr-img",
            "figure[data-index] img",
            ".read-viewer .page img",
            ".read-viewer img",
            ".viewer-wrapper img",
            "div.page-break img",
            ".main-col-inner img",
            "#readerarea img",
            ".reading-content img",
            ".page-break img",
            ".chapter-content img",
            ".wt_viewer img",
            "#chapter_area img",
            ".manga-reader img",
            "[aria-label*='Chapter'] img",
            ".read-container img",
            "#chapter_boxImages img",
            "#toon_img img",
            ".image_story img",
            ".imageChap img",
            ".img-responsive.image-chapter",
            ".mr-img",
            "article.prose img",
            "main#main-content img",
            ".manga-pages img",
            ".manga-page img",
            ".page-container img",
            "img.manga-image",
        ]

        for sel in selectors:
            elements = soup.select(sel)
            if elements:
                self.log_message(
                    f"Hit: {len(elements)} images with {sel[:30]}...", "info"
                )
                for img in elements:
                    for src in self._get_img_sources(img, base_url):
                        if src:
                            candidates.add(src)

        if len(candidates) < 6:
            self.log_message("Plan B: searching all containers for images...", "warn")
            containers = soup.find_all(["div", "section", "article", "main"])
            best = max(containers, key=lambda d: len(d.find_all("img")), default=None)
            if best:
                imgs = best.find_all("img")
                self.log_message(f"Found container with {len(imgs)} images", "info")
                for img in imgs:
                    for src in self._get_img_sources(img, base_url):
                        if src:
                            candidates.add(src)

        if len(candidates) < 5:
            self.log_message(
                "Plan C: unleashing the regex beast (that was cringe)", "warn"
            )
            rx = re.findall(
                r'https?://[^\s"\'<>]+\.(?:jpe?g|png|webp|avif)(?:\?[^\s"\'<>]*)?',
                html,
                re.I,
            )
            candidates.update(rx)

        filtered = []
        seen = set()
        for u in candidates:
            if u in seen:
                continue
            seen.add(u)
            if self._is_valid_image_url(u, base_url):
                filtered.append(u)

        def num_key(s):
            patterns = [
                r"ch[_-]?\d+[_-](\d+)",
                r"/(\d+)\.(?:jpg|jpeg|png|webp)",
                r"page[_-]?(\d+)",
                r"c_\d+_(\d+)",
                r"(\d+)(?:-\d+)?\.(?:jpg|jpeg|png|webp)",
            ]
            for pattern in patterns:
                m = re.search(pattern, s.lower())
                if m:
                    return int(m.group(1))
            return 999999  # idk

        filtered.sort(key=num_key)

        completed_urls = self._complete_sequential_patterns(filtered, base_url, soup)
        if len(completed_urls) > len(filtered):
            self.log_message(
                f"🔍 Pattern detection: Found {len(completed_urls) - len(filtered)} additional images!",
                "ok",
            )
            filtered = completed_urls

        self.log_message(f"Got {len(filtered)} clean images ready to download", "ok")
        return filtered

    def _complete_sequential_patterns(
        self, urls: list, base_url: str, soup=None
    ) -> list:
        if len(urls) < 3:
            return urls

        # Try to find a common base URL and number pattern
        # Pattern: /path/01.ext, 02.ext, 03.ext, etc.
        pattern_match = re.search(r"^(.*?)(\d{2,3})(\.[\w]+)(?:\?.*)?$", urls[0])
        if not pattern_match:
            return urls

        base_part = pattern_match.group(1)
        ext_part = pattern_match.group(3)

        verified = True
        numbers_found = []
        number_strings = []
        for url in urls[:5]:
            match = re.search(
                r"^" + re.escape(base_part) + r"(\d{2,3})" + re.escape(ext_part), url
            )
            if match:
                number_strings.append(match.group(1))
                numbers_found.append(int(match.group(1)))
            else:
                verified = False
                break

        if not verified or len(numbers_found) < 2:
            return urls

        # Check if the HTML hints at how many images there should be
        # Look for progress bar like "1/11" or count empty page divs
        expected_count = self._estimate_total_images(soup)

        if expected_count <= len(urls):
            return urls  # We already have all images (this should work for comix.to where they show all images but some are hidden until you scroll)

        min_num = min(numbers_found)
        max_num = max(numbers_found)
        if expected_count > max_num:
            max_num = expected_count
        complete_urls = []
        existing_urls_set = set(urls)
        num_digits = (
            len(number_strings[0]) if number_strings else 2
        )  # Gonna use original string length to preserve the leading zeros

        for num in range(min_num, max_num + 1):
            url = f"{base_part}{num:0{num_digits}d}{ext_part}"
            if url in existing_urls_set:
                complete_urls.append(next(u for u in urls if u.startswith(url)))
            else:
                complete_urls.append(url)

        return complete_urls if len(complete_urls) > len(urls) else urls

    def _estimate_total_images(self, soup) -> int:
        """
        This function right here is just to estimate how many images should be on the page based on the HTML structure.
        pattern right?????? right?????!!!!!!!!.
        """
        if not soup:
            return 0

        # Method 0: comix.to uses data-page attributes on page containers
        page_elements = soup.select("[data-page]")
        if page_elements:
            max_page = max(
                (
                    int(el.get("data-page", 0))
                    for el in page_elements
                    if el.get("data-page", "").isdigit()
                ),
                default=0,
            )
            if max_page > 0:
                self.log_message(
                    f"detected {max_page} pages from data-page attributes (comix.to)",
                    "info",
                )
                return max_page

        # Method 1: count empty page divs in viewer wrappers (comix.to style)
        page_divs = soup.select(
            ".viewer-wrapper .page, .read-viewer .page, .rpage-page"
        )
        if page_divs:
            total_divs = len(page_divs)
            if total_divs > 0:
                self.log_message(
                    f"detected {total_divs} page containers in HTML", "info"
                )
                return total_divs

        # Method 2: look for progress bar line like "1/11"
        progress = soup.select_one(".progress-line")
        if progress:
            text = progress.get_text(strip=True)
            # extract numbers like "111" meaning page 1 to 11
            if len(text) >= 2 and text.isdigit():
                # pattern: "111" = page 1 to 11
                last_digit = int(text[-1])
                remaining = text[:-1]
                if remaining.isdigit():
                    total = int(remaining + text[-1])
                    if total > last_digit:
                        self.log_message(
                            f"detected {total} pages from progress bar", "info"
                        )
                        return total

        return 0

    def _get_img_sources(self, img, base):
        attrs = [
            "data-src",
            "src",
            "data-lazy-src",
            "data-original",
            "data-lazy",
            "data-srcset",
            "srcset",
        ]
        srcs = []
        for a in attrs:
            v = img.get(a)
            if v and v.strip():
                if any(
                    p in v.lower()
                    for p in ["/1x1.", "placeholder", "loading", "lazy.", "data:image"]
                ):
                    continue
                if a in ["srcset", "data-srcset"]:
                    v = v.split(",")[0].strip().split()[0]
                full = self.normalize_url(v, base)
                if full and full.startswith(("http://", "https://")):
                    srcs.append(full)
        return srcs

    def normalize_url(self, src: str, base: str) -> str:
        src = (src or "").strip()
        if not src:
            return ""
        if src.startswith("//"):
            return "https:" + src
        if src.startswith("/"):
            return urljoin(base, src)
        if not src.startswith(("http://", "https://")):
            return urljoin(base, src)
        return src

    def _is_valid_image_url(self, url: str, chapter_url: str) -> bool:
        if not url.startswith(("http", "https")):
            return False

        low = url.lower()

        if self.exclude_gifs_var.get() and low.endswith(".gif"):
            return False

        placeholders = [
            "/1x1.",
            "placeholder",
            "loading.",
            "lazy.",
            "blank.",
            "transparent.",
        ]
        if any(p in low for p in placeholders):
            return False

        junk = [
            "logo",
            "banner",
            "icon",
            "avatar",
            "thumb",
            "cover.webp",
            "cover.jpg",
            "ad-",
            "advert",
            "emoji",
            "999.png",
            "discord.webp",
            "facebook",
            "twitter",
            "instagram",
            "patreon",
            "kofi",
            "paypal",
            "donate",
            "sprite",
            "button",
            "read_on_flame",
            "commission",
            "message.png",
            "reaction",
            "sticker",
            "emote",
            "smil",
            "face-",
            "icon-",
            "ui-",
        ]

        if self.aggressive_comments_var.get():
            junk += ["comment", "disqus", "reply", "fb_", "social", "share", "widget"]

        if any(k in low for k in junk):
            return False

        good = [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            "cdn",
            "scans",
            "storage",
            "media",
            "image",
            "chapter",
            "manga",
            "manhwa",
            "manhua",
            "tnlycdn",
            "lastation",
            "toonily",
            "manhwazone",
            "manhwatop",
            "comix",
            "wowpic",
            "data.",
            "flamecomics",
            "mangaball",
            "kuramanga",
            "luacomic",
            "shadowabyss",
            "jigglypuff",
            "poke-black-and-white",
            "cocomic",
            "img.cocomic",
            "rpage",
        ]

        return any(x in low for x in good)

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

        comic = (
            re.sub(
                r"(Manhwa|Manga|Manhua|Read|Online|Latest).*", "", comic, flags=re.I
            ).strip()
            or "Comic"
        )
        chapter = (
            re.sub(
                r"(Chapter|Episode|Ch\.?|Ep\.?)\s*", "Ch. ", chapter, flags=re.I
            ).strip()
            or "Chapter"
        )

        return Path(base_dir) / self._sanitize(comic) / self._sanitize(chapter)

    def _sanitize(self, s: str) -> str:
        s = re.sub(r'[<>:"/\\|?*]', "", s)
        return re.sub(r"\s+", " ", s).strip()[:85] or "Unknown"

    def _complete_sequential_urls(self, urls: list, html: str) -> list:
        if len(urls) < 3:
            return urls  # 3 to detect pattern

        # numbered URLs like 01.webp, 02.webp, and etc
        pattern_match = re.search(r"(.+/)(\d{2,3})\.(webp|jpg|jpeg|png)", urls[0])
        if not pattern_match:
            return urls

        base_url = pattern_match.group(1)
        first_num = int(pattern_match.group(2))
        ext = pattern_match.group(3)
        num_digits = len(pattern_match.group(2))

        # verification on all URLs that follow this pattern
        sequential = []
        for url in urls:
            match = re.search(r"(\d{2,3})\." + ext + r"$", url)
            if match and url.startswith(base_url):
                sequential.append(int(match.group(1)))

        if len(sequential) < 3:
            return urls  # pattern doesn't match enough URLs

        # checking for the page count in HTML( with the common patterns)
        page_indicators = [
            r"<div>(\d+)</div>.*?progress",  # progress bar
            r'"pages?"\s*:\s*(\d+)',  # JSON page count
            r"Page\s+\d+\s+of\s+(\d+)",  # "Page 1 of 11"
            r"(\d+)\s+pages?",  # "11 pages"
        ]

        max_page = max(sequential)
        for pattern in page_indicators:
            match = re.search(pattern, html, re.I)
            if match:
                detected_count = int(match.group(1))
                if detected_count > max_page and detected_count < 200:
                    max_page = detected_count
                    self.log_message(
                        f"Detected {detected_count} total pages (completing lazy-loaded URLs...)",
                        "info",
                    )
                    break

        # generates missing URLs
        completed = list(urls)
        existing_nums = set(sequential)

        for num in range(first_num, max_page + 1):
            if num not in existing_nums:
                padded_num = str(num).zfill(num_digits)
                new_url = f"{base_url}{padded_num}.{ext}"
                completed.append(new_url)

        # we sort by numbers
        def get_num(url):
            match = re.search(r"(\d{2,3})\." + ext + r"$", url)
            return int(match.group(1)) if match else 9999

        return sorted(completed, key=get_num)

    def generate_cbz(self, output_dir: Path, image_paths: list):
        try:
            cbz_path = output_dir / f"{output_dir.name}.cbz"
            with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for img_path in sorted(image_paths):
                    # Soooo cbz breaks from webp image idk why, so i just added a convert to JPG
                    if (
                        self.convert_webp_cbz_var.get()
                        and img_path.suffix.lower() == ".webp"
                        and PIL_AVAILABLE
                    ):
                        try:
                            from PIL import Image as PILImage

                            img = PILImage.open(img_path)

                            if img.mode in ("RGBA", "LA", "P"):
                                background = PILImage.new(
                                    "RGB", img.size, (255, 255, 255)
                                )
                                if img.mode == "P":
                                    img = img.convert("RGBA")
                                background.paste(
                                    img,
                                    mask=img.split()[-1]
                                    if img.mode == "RGBA"
                                    else None,
                                )
                                img = background
                            elif img.mode != "RGB":
                                img = img.convert("RGB")

                            jpg_name = img_path.stem + ".jpg"

                            # (big brain move :p))
                            jpg_buffer = io.BytesIO()
                            img.save(
                                jpg_buffer, format="JPEG", quality=95, optimize=True
                            )
                            jpg_buffer.seek(0)
                            zf.writestr(jpg_name, jpg_buffer.read())
                            self.log_message(
                                f"  Converted {img_path.name} → {jpg_name}", "info"
                            )
                        except Exception as e:
                            # Conversion failed, so just add the original (we YOLO this)
                            zf.write(img_path, img_path.name)
                            self.log_message(
                                f"  Couldn't convert {img_path.name}, added as-is",
                                "warn",
                            )
                    else:
                        zf.write(img_path, img_path.name)

            self.log_message(f"✓ CBZ archive created: {cbz_path.name}", "ok")
            return True
        except Exception as e:
            self.log_message(f"✗ CBZ creation failed: {e}", "error")
            return False

    def generate_pdf(self, output_dir: Path):
        try:
            images = sorted(
                [
                    p
                    for p in output_dir.iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                ],
                key=lambda x: (
                    int(re.search(r"(\d+)", x.stem).group(1))
                    if re.search(r"(\d+)", x.stem)
                    else 0
                ),
            )
            if not images:
                raise ValueError("No images found for PDF generation")

            imgs = [Image.open(p).convert("RGB") for p in images]
            pdf_path = output_dir / f"{output_dir.name}.pdf"
            imgs[0].save(
                pdf_path, "PDF", resolution=100.0, save_all=True, append_images=imgs[1:]
            )
            self.log_message(f"✓ PDF document created: {pdf_path.name}", "ok")
            return True
        except Exception as e:
            self.log_message(f"✗ PDF generation failed: {e}", "error")
            return False

    def generate_epub(self, output_dir: Path):
        try:
            book = epub.EpubBook()
            book.set_identifier(f"comic-{time.time()}")
            book.set_title(f"{output_dir.parent.name} - {output_dir.name}")
            book.add_author("Downloaded via Universal Comic Downloader")
            book.set_language("en")

            chapters = []
            images = sorted(
                [
                    p
                    for p in output_dir.iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                ],
                key=lambda x: (
                    int(re.search(r"(\d+)", x.stem).group(1))
                    if re.search(r"(\d+)", x.stem)
                    else 0
                ),
            )

            for i, img_path in enumerate(images, 1):
                img_item = epub.EpubItem(
                    uid=f"image_{i}",
                    file_name=f"images/page_{i:03d}{img_path.suffix}",
                    media_type="image/jpeg"
                    if img_path.suffix.lower() in (".jpg", ".jpeg")
                    else "image/png",
                    content=img_path.read_bytes(),
                )
                book.add_item(img_item)

                chapter = epub.EpubHtml(
                    title=f"Page {i}", file_name=f"page_{i:03d}.xhtml"
                )
                chapter.content = f'<div><img src="{img_item.file_name}" style="max-width:100%;height:auto;" /></div>'
                book.add_item(chapter)
                chapters.append(chapter)

            book.toc = chapters
            book.spine = ["nav"] + chapters
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            epub_path = output_dir / f"{output_dir.name}.epub"
            epub.write_epub(str(epub_path), book)
            self.log_message(f"✓ EPUB ebook created: {epub_path.name}", "ok")
            return True
        except Exception as e:
            self.log_message(f"✗ EPUB generation failed: {e}", "error")
            return False

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
    app = UniversalComicDownloader(root)
    root.mainloop()
