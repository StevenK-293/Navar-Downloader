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
        label = tk.Label(self.tooltip, text=self.text, background="#ffffe0",
                        relief="solid", borderwidth=1, padx=6, pady=4)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class UniversalComicDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Comic Downlaoder - Download any comic images.")
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
            self.log_message("⚠ Browser mode MIA - run: pip install playwright && playwright install", "warn")

        if PIL_AVAILABLE:
            self.log_message("✓ Image wizardry enabled", "ok")
        else:
            self.log_message("⚠ No Pillow, no PDF party (install: pip install pillow)", "warn")

        if EPUB_AVAILABLE:
            self.log_message("✓ EPUB factory operational", "ok")
        else:
            self.log_message("⚠ EPUB machine broke (install: pip install ebooklib)", "warn")

        self.log_message("✓ CBZ archives always ready", "ok")
        self.log_message("-" * 60, "info")
        self.log_message("Drop a URL and download image", "info")
        self.log_message("", "info")

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'), foreground='#667eea')
        style.configure('Subtitle.TLabel', font=('Segoe UI', 9), foreground='#718096')
        style.configure('Header.TLabel', font=('Segoe UI', 10, 'bold'), foreground='#2d3748')
        style.configure('Info.TLabel', font=('Segoe UI', 9), foreground='#718096')
        style.configure('Status.TLabel', font=('Segoe UI', 10), foreground='#667eea')
        style.configure('TButton', font=('Segoe UI', 9), padding=10)
        style.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'), padding=12)
        style.configure('TLabelframe', borderwidth=2, relief='flat')
        style.configure('TLabelframe.Label', font=('Segoe UI', 9, 'bold'), foreground='#4a5568')
        
        main = ttk.Frame(self.root, padding="20")
        main.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        ttk.Label(header_frame, text="Comic Downloader", 
                 style='Title.TLabel').pack(side=tk.LEFT)
        ttk.Label(header_frame, text=" • Because manually downloading is for peasants",
                 style='Subtitle.TLabel').pack(side=tk.LEFT, padx=(8, 0))

        url_frame = ttk.LabelFrame(main, text=" 🔗 Chapter URL ", padding=8)
        url_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Segoe UI", 10))
        url_entry.pack(fill="x", pady=(0, 4))
        
        # ttk.Label(url_frame, text="",
        #          foreground="#4CAF50", font=("Segoe UI", 8)).pack(anchor="w")

        save_frame = ttk.LabelFrame(main, text=" 💾 Save Location ", padding=8)
        save_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        
        path_frame = ttk.Frame(save_frame)
        path_frame.pack(fill="x")
        
        ttk.Entry(path_frame, textvariable=self.output_var, font=("Segoe UI", 9)).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(path_frame, text="Browse", command=self.choose_folder, width=10).pack(side="right")

        opt = ttk.LabelFrame(main, text=" ⚙️ Options ", padding=8)
        opt.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        left_col = ttk.Frame(opt)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ttk.Checkbutton(left_col, text="Use Browser Mode (recommended for protected sites)",
                       variable=self.use_browser_var).pack(anchor="w", pady=1)
        ttk.Checkbutton(left_col, text="Convert WEBP to JPG (better compatibility)", 
                       variable=self.convert_webp_var).pack(anchor="w", pady=1)
        ttk.Checkbutton(left_col, text="Skip GIF images", 
                       variable=self.exclude_gifs_var).pack(anchor="w", pady=1)
        ttk.Checkbutton(left_col, text="Skip small images (emojis, icons, ads)", 
                       variable=self.skip_tiny_var).pack(anchor="w", pady=1)
        ttk.Checkbutton(left_col, text="Aggressive filtering (remove comments/widgets)",
                       variable=self.aggressive_comments_var).pack(anchor="w", pady=1)
        
        right_col = ttk.Frame(opt)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right_col, text="Export as:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Checkbutton(right_col, text="CBZ (Comic Book Archive)", 
                       variable=self.generate_cbz_var).pack(anchor="w", pady=1)
        
        cbz_option_frame = ttk.Frame(right_col)
        cbz_option_frame.pack(anchor="w", padx=(20, 0), pady=0)
        ttk.Checkbutton(cbz_option_frame, text="Convert WEBP→JPG in CBZ", 
                       variable=self.convert_webp_cbz_var,
                       state="normal" if PIL_AVAILABLE else "disabled").pack(anchor="w", pady=1)
        
        ttk.Checkbutton(right_col, text="PDF Document", variable=self.generate_pdf_var,
                       state="normal" if PIL_AVAILABLE else "disabled").pack(anchor="w", pady=1)
        ttk.Checkbutton(right_col, text="EPUB eBook", variable=self.generate_epub_var,
                       state="normal" if EPUB_AVAILABLE and PIL_AVAILABLE else "disabled").pack(anchor="w", pady=1)

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 15))

        self.test_btn = ttk.Button(btn_frame, text="🔍 Test URL", command=self.test_url, width=15)
        self.test_btn.pack(side="left", padx=(0, 8))
        
        self.start_btn = ttk.Button(btn_frame, text="▶️ Start Download", command=self.start_download, 
                                    style='Primary.TButton', width=18)
        self.start_btn.pack(side="left", padx=(0, 8))
        
        self.cancel_btn = ttk.Button(btn_frame, text="⏹️ Cancel", state="disabled", command=self.cancel, width=12)
        self.cancel_btn.pack(side="left", padx=(0, 15))
        
        ttk.Button(btn_frame, text="📁 Open Folder", command=self.open_folder, width=14).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="🗑️ Clear Log", command=self.clear_log, width=12).pack(side="left")

        progress_frame = ttk.LabelFrame(main, text=" 📊 Progress ", padding=8)
        progress_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        
        status_line = ttk.Frame(progress_frame)
        status_line.pack(fill="x", pady=(0, 8))
        ttk.Label(status_line, text="Status:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        ttk.Label(status_line, textvariable=self.current_status, foreground="#1976D2",
                 font=("Segoe UI", 9)).pack(side="left")
        
        prog_container = ttk.Frame(progress_frame)
        prog_container.pack(fill="x", pady=(0, 8))
        
        self.progress = ttk.Progressbar(prog_container, mode="determinate", variable=self.progress_value)
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(prog_container, textvariable=self.progress_label, width=8, 
                 font=("Segoe UI", 9, "bold")).pack(side="right")
        
        info_line = ttk.Frame(progress_frame)
        info_line.pack(fill="x")
        ttk.Label(info_line, textvariable=self.images_found, foreground="#666666",
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 15))
        ttk.Label(info_line, textvariable=self.images_downloaded, foreground="#666666",
                 font=("Segoe UI", 8)).pack(side="left")

        log_frame = ttk.LabelFrame(main, text=" 📝 Activity Log ", padding=8)
        log_frame.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(0, 0))

        self.log = scrolledtext.ScrolledText(log_frame, height=14, font=("Consolas", 9),
                                            bg="#ffffff", wrap="word", relief="flat", borderwidth=1)
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("info", foreground="#4a5568")
        self.log.tag_config("ok", foreground="#48bb78")
        self.log.tag_config("warn", foreground="#ed8936")
        self.log.tag_config("error", foreground="#f56565")

        main.columnconfigure(0, weight=1)
        main.rowconfigure(6, weight=1)

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
        self.update_status("Cancelling... (stopping after current image)")
        self.log_message("Cancelling download - stopping after current image completes...", "warn")

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
                    self.log_message(f"  ... and {len(imgs)-10} more", "info")
                self.log_message("✓ Ready to download! Click 'Start Download' to begin.", "ok")
        except Exception as e:
            self.log_message(f"✗ Test failed: {str(e)[:180]}", "error")
            self.log_message("Please check the URL and try again", "warn")
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
            
            self.current_step.set("Step 1/4: Fetching page...")
            self.update_status(f"Loading chapter page using {'Browser Mode' if use_browser else 'Direct Request'}...")
            self.log_message(f"Method: {'Browser Mode (Playwright)' if use_browser else 'Direct HTTP Request'}", "info")
            html = self.fetch_page(chapter_url, use_browser)
            self.log_message("✓ Page loaded successfully", "ok")

            self.current_step.set("Step 2/4: Finding images...")
            self.update_status("Analyzing page and extracting image URLs...")
            image_urls = self.extract_image_urls(html, chapter_url)

            if not image_urls:
                self.log_message("✗ Found absolutely nothing. This page is a ghost town.", "error")
                if not use_browser:
                    self.log_message("Try enabling Browser Mode - maybe that'll help", "warn")
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
            
            browser_images = {}
            if use_browser and PLAYWRIGHT_AVAILABLE:
                self.log_message("Attempting batch download with browser...", "info")
                self.update_status("Using browser to capture all images at once...")
                browser_images = self.batch_download_with_browser(chapter_url, image_urls)
                if browser_images:
                    self.log_message(f"✓ Successfully captured {len(browser_images)} images from browser", "ok")

            for i, img_url in enumerate(image_urls, 1):
                if not self.running:
                    self.log_message("", "info")
                    self.log_message("=" * 60, "warn")
                    self.log_message(f"✗ Cancelled: User said 'nah I'm good' - Saved {success}/{self.total_images} images", "warn")
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
                    
                    if img_url in browser_images:
                        content = browser_images[img_url]
                        size_kb = len(content) // 1024
                        self.log_message(f"  Size: {size_kb} KB", "info")
                        self.log_message("  ✓ Using cached image from browser", "ok")
                    else:
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
                            r = requests.get(img_url, headers=headers, timeout=20, stream=True, allow_redirects=True)
                            r.raise_for_status()
                            content = r.content
                            size_kb = len(content) // 1024
                            self.log_message(f"  Size: {size_kb} KB", "info")
                        except requests.exceptions.HTTPError as e:
                            if "403" in str(e) and use_browser and PLAYWRIGHT_AVAILABLE:
                                self.log_message("  Got 403'd, trying browser mode...", "warn")
                                content = self.download_image_with_browser(img_url, chapter_url)
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
                            if filename.lower().endswith('.png') and PIL_AVAILABLE:
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
                                self.log_message("  ⚠ Skipped (sus smol boi - probably emoji/icon)", "warn")
                                continue
                            else:
                                questionable_dir.mkdir(parents=True, exist_ok=True)
                                questionable_path = questionable_dir / filename
                                with open(questionable_path, "wb") as f:
                                    f.write(content)
                                self.log_message(f"  ⚠ Quarantined to _questionable_images ({len(content)//1024} KB)", "warn")
                                continue

                    if self.convert_webp_var.get() and PIL_AVAILABLE:
                        if filename.lower().endswith(('.webp', '.png')) or img_url in browser_images:
                            try:
                                from PIL import Image as PILImage
                                img = PILImage.open(io.BytesIO(content))
                                
                                if img.mode in ('RGBA', 'LA', 'P'):
                                    background = PILImage.new('RGB', img.size, (255, 255, 255))
                                    if img.mode == 'P':
                                        img = img.convert('RGBA')
                                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                    img = background
                                elif img.mode != 'RGB':
                                    img = img.convert('RGB')
                                
                                jpg_path = save_path.with_suffix('.jpg')
                                img.save(jpg_path, 'JPEG', quality=95, optimize=True)
                                
                                save_path = jpg_path
                                filename = jpg_path.name
                                self.log_message(f"  ✓ Converted to JPG ({len(content)//1024} KB → {jpg_path.stat().st_size//1024} KB)", "ok")
                            except Exception as e:
                                with open(save_path, "wb") as f:
                                    f.write(content)
                                self.log_message(f"  ⚠ Conversion failed ({str(e)[:50]}), saved anyway", "warn")
                        else:
                            with open(save_path, "wb") as f:
                                f.write(content)
                    else:
                        with open(save_path, "wb") as f:
                            f.write(content)

                    success += 1
                    saved_paths.append(save_path)
                    self.images_downloaded.set(f"Downloaded: {success}/{self.total_images}")
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
                self.log_message(f"✓ All done! Successfully yoinked {success}/{self.total_images} images", "ok")
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

            if self.running and self.generate_epub_var.get() and EPUB_AVAILABLE and PIL_AVAILABLE:
                self.current_step.set("Step 4/4: Creating EPUB file...")
                self.update_status("Generating EPUB ebook...")
                if self.generate_epub(output_dir):
                    exports_created.append("EPUB")
            
            if exports_created:
                self.log_message(f"✓ Generated formats: {', '.join(exports_created)}", "ok")
            
            self.current_step.set("Complete!")
            self.update_status("All done! Ready for next download")

        except Exception as e:
            self.log_message(f"Everything exploded: {e}", "error")
        finally:
            self._finish()

    def batch_download_with_browser(self, chapter_url: str, image_urls: list) -> dict:
        if not PLAYWRIGHT_AVAILABLE:
            return {}
        
        try:
            self.log_message("Launching sneaky browser...", "info")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    ignore_https_errors=True
                )
                
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                page = context.new_page()
                
                self.log_message("Loading page...", "info")
                page.goto(chapter_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3500)
                
                self.log_message("Scrolling like a madman to trigger lazy images...", "info")
                page_height = page.evaluate("document.body.scrollHeight")
                viewport_height = page.evaluate("window.innerHeight")
                
                scroll_steps = max(20, int(page_height / viewport_height) + 5)
                for i in range(scroll_steps):
                    page.evaluate(f"window.scrollTo(0, {i * viewport_height * 0.8})")
                    page.wait_for_timeout(400)
                
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)
                
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(1000)
                
                self.log_message("Ripping images from browser memory...", "info")
                images_data = page.evaluate("""
                    async () => {
                        const results = {};
                        const images = document.querySelectorAll('img');
                        
                        for (const img of images) {
                            try {
                                const src = img.src || img.dataset.src || img.dataset.lazySrc;
                                if (!src || src.includes('data:image') || src.includes('1x1')) continue;
                                
                                if (!img.complete) {
                                    await new Promise((resolve) => {
                                        img.onload = resolve;
                                        img.onerror = resolve;
                                        setTimeout(resolve, 2000);
                                    });
                                }
                                
                                if (!img.naturalWidth || !img.naturalHeight) continue;
                                
                                const canvas = document.createElement('canvas');
                                canvas.width = img.naturalWidth;
                                canvas.height = img.naturalHeight;
                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(img, 0, 0);
                                
                                const dataUrl = canvas.toDataURL('image/png', 0.95);
                                results[src] = dataUrl.split(',')[1];
                            } catch (e) {
                                // this image is cursed, moving on...
                            }
                        }
                        
                        return results;
                    }
                """)
                
                context.close()
                browser.close()
                
                images_dict = {}
                for url, b64_data in images_data.items():
                    try:
                        images_dict[url] = base64.b64decode(b64_data)
                    except:
                        pass
                
                return images_dict
                
        except Exception as e:
            self.log_message(f"Browser batch download failed: {str(e)[:100]}", "warn")
            return {}

    def download_image_with_browser(self, img_url: str, referer_url: str) -> bytes:
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed, can't browser mode this")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ])
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    extra_http_headers={
                        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    ignore_https_errors=True
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
                
                response = page.goto(img_url, wait_until="domcontentloaded", timeout=20000)
                if response and response.ok:
                    content = response.body()
                    context.close()
                    browser.close()
                    return content
                else:
                    context.close()
                    browser.close()
                    raise ValueError(f"Download failed with status {response.status if response else 'unknown'}")
                    
        except Exception as e:
            raise RuntimeError(f"Browser download error: {str(e)}")

    def fetch_page(self, url: str, use_browser: bool) -> str:
        if use_browser and PLAYWRIGHT_AVAILABLE:
            for attempt in range(1, 4):
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
                        context = browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            viewport={"width": 1280, "height": 900}
                        )
                        page = context.new_page()

                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=60000)
                            page.wait_for_timeout(2500)

                            page.evaluate("""
                                () => {
                                    document.querySelectorAll('img[data-src], img[data-lazy], img[data-lazy-src], img[data-original]').forEach(img => {
                                        if (img.dataset.src) img.src = img.dataset.src;
                                        if (img.dataset.lazy) img.src = img.dataset.lazy;
                                        if (img.dataset.lazySrc) img.src = img.dataset.lazySrc;
                                        if (img.dataset.original) img.src = img.dataset.original;
                                    });
                                }
                            """)

                            page_height = page.evaluate("document.body.scrollHeight")
                            viewport_height = page.evaluate("window.innerHeight")
                            scroll_steps = max(25, int(page_height / viewport_height) + 5)
                            
                            for i in range(scroll_steps):
                                page.evaluate(f"window.scrollTo(0, {i * viewport_height * 0.75})")
                                page.wait_for_timeout(500)
                            
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            page.wait_for_timeout(2000)
                            page.evaluate("window.scrollTo(0, 0)")
                            page.wait_for_timeout(1000)

                            html = page.content()
                            if len(html) < 4000:
                                raise ValueError("Sus page, too short")
                            return html
                        finally:
                            context.close()
                            browser.close()
                except Exception as e:
                    self.log_message(f"Browser attempt {attempt}/3 failed: {str(e)[:100]}", "warn")
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

        selectors = [
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
            
            # uhhh just patternss
            "section[aria-label*='Chapter'] img.lazy-image", "figure[data-index] img.mr-img",
            "figure[data-index] img", ".read-viewer .page img", ".read-viewer img",
            ".viewer-wrapper img", ".reading-content img.wp-manga-chapter-img",
            ".entry-content img.wp-manga-chapter-img", "div.page-break img",
            ".main-col-inner img", "#readerarea img", ".reading-content img", 
            ".page-break img", ".chapter-content img", ".wt_viewer img",
            "#chapter_area img", ".manga-reader img", "[aria-label*='Chapter'] img", 
            ".read-container img", "#chapter_boxImages img", "#toon_img img", 
            ".image_story img", ".imageChap img", ".img-responsive.image-chapter",
            ".mr-img", "article.prose img", "main#main-content img"
        ]

        for sel in selectors:
            elements = soup.select(sel)
            if elements:
                self.log_message(f"Hit: {len(elements)} images with {sel[:30]}...", "info")
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
            self.log_message("Plan C: unleashing the regex beast (that was cringe)", "warn")
            rx = re.findall(r'https?://[^\s"\'<>]+\.(?:jpe?g|png|webp|avif)(?:\?[^\s"\'<>]*)?', html, re.I)
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
                r'ch[_-]?\d+[_-](\d+)', r'/(\d+)\.(?:jpg|jpeg|png|webp)',
                r'page[_-]?(\d+)', r'c_\d+_(\d+)',
                r'(\d+)(?:-\d+)?\.(?:jpg|jpeg|png|webp)',
            ]
            for pattern in patterns:
                m = re.search(pattern, s.lower())
                if m:
                    return int(m.group(1))
            return 999999
        
        filtered.sort(key=num_key)
        
        completed_urls = self._complete_sequential_patterns(filtered, base_url, soup)
        if len(completed_urls) > len(filtered):
            self.log_message(f"🔍 Pattern detection: Found {len(completed_urls) - len(filtered)} additional images!", "ok")
            filtered = completed_urls
        
        self.log_message(f"Got {len(filtered)} clean images ready to download", "ok")
        return filtered

    def _complete_sequential_patterns(self, urls: list, base_url: str, soup=None) -> list:
        if len(urls) < 3:
            return urls
        
        # Try to find a common base URL and number pattern
        # Pattern: /path/01.ext, 02.ext, 03.ext, etc.
        pattern_match = re.search(r'^(.*?)(\d{2,3})(\.[\w]+)(?:\?.*)?$', urls[0])
        if not pattern_match:
            return urls 
        
        base_part = pattern_match.group(1)
        ext_part = pattern_match.group(3)
        
        verified = True
        numbers_found = []
        number_strings = []
        for url in urls[:5]:
            match = re.search(r'^' + re.escape(base_part) + r'(\d{2,3})' + re.escape(ext_part), url)
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
        num_digits = len(number_strings[0]) if number_strings else 2  # Gonna use original string length to preserve the leading zeros
        
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
        
        # Method 1: count empty page divs in viewer wrappers (comix.to style)
        page_divs = soup.select(".viewer-wrapper .page, .read-viewer .page")
        if page_divs:
            total_divs = len(page_divs)
            if total_divs > 0:
                self.log_message(f"detected {total_divs} page containers in HTML", "info")
                return total_divs
        
        # Method 2: look for progress bar line like "1/11"
        progress = soup.select_one(".progress-line")
        if progress:
            text = progress.get_text(strip=True)
            #extract numbers like "111" meaning page 1 to 11
            if len(text) >= 2 and text.isdigit():
                # pattern: "111" = page 1 to 11
                last_digit = int(text[-1])
                remaining = text[:-1]
                if remaining.isdigit():
                    total = int(remaining + text[-1])
                    if total > last_digit:
                        self.log_message(f"detected {total} pages from progress bar", "info")
                        return total
        
        return 0

    def _get_img_sources(self, img, base):
        attrs = ["data-src", "src", "data-lazy-src", "data-original", "data-lazy", "data-srcset", "srcset"]
        srcs = []
        for a in attrs:
            v = img.get(a)
            if v and v.strip():
                if any(p in v.lower() for p in ['/1x1.', 'placeholder', 'loading', 'lazy.', 'data:image']):
                    continue
                if a in ["srcset", "data-srcset"]:
                    v = v.split(",")[0].strip().split()[0]
                full = self.normalize_url(v, base)
                if full and full.startswith(('http://', 'https://')):
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
        if not url.startswith(("http", "https")): 
            return False
        
        low = url.lower()

        if self.exclude_gifs_var.get() and low.endswith(".gif"): 
            return False
        
        placeholders = ['/1x1.', 'placeholder', 'loading.', 'lazy.', 'blank.', 'transparent.']
        if any(p in low for p in placeholders):
            return False

        junk = [
            "logo", "banner", "icon", "avatar", "thumb", "cover.webp", "cover.jpg",
            "ad-", "advert", "emoji", "999.png", "discord.webp", "facebook", "twitter",
            "instagram", "patreon", "kofi", "paypal", "donate", "sprite", "button",
            "read_on_flame", "commission", "message.png", "reaction", "sticker",
            "emote", "smil", "face-", "icon-", "ui-"
        ]
        
        if self.aggressive_comments_var.get():
            junk += ["comment", "disqus", "reply", "fb_", "social", "share", "widget"]

        if any(k in low for k in junk): 
            return False

        good = [
            ".jpg", ".jpeg", ".png", ".webp", "cdn", "scans", "storage", "media", 
            "image", "chapter", "manga", "manhwa", "manhua", "tnlycdn", "lastation", 
            "toonily", "manhwazone", "manhwatop", "comix", "wowpic", "data.",
            "flamecomics", "mangaball", "kuramanga", "luacomic", "shadowabyss",
            "jigglypuff", "poke-black-and-white"
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

        comic = re.sub(r'(Manhwa|Manga|Manhua|Read|Online|Latest).*', '', comic, flags=re.I).strip() or "Comic"
        chapter = re.sub(r'(Chapter|Episode|Ch\.?|Ep\.?)\s*', 'Ch. ', chapter, flags=re.I).strip() or "Chapter"

        return Path(base_dir) / self._sanitize(comic) / self._sanitize(chapter)

    def _sanitize(self, s: str) -> str:
        s = re.sub(r'[<>:"/\\|?*]', '', s)
        return re.sub(r'\s+', ' ', s).strip()[:85] or "Unknown"
    def _complete_sequential_urls(self, urls: list, html: str) -> list:
        if len(urls) < 3:
            return urls  #3 to detect pattern
        
        #numbered URLs like 01.webp, 02.webp, and etc
        pattern_match = re.search(r'(.+/)(\d{2,3})\.(webp|jpg|jpeg|png)', urls[0])
        if not pattern_match:
            return urls
        
        base_url = pattern_match.group(1)
        first_num = int(pattern_match.group(2))
        ext = pattern_match.group(3)
        num_digits = len(pattern_match.group(2))
        
        # verification on all URLs that follow this pattern
        sequential = []
        for url in urls:
            match = re.search(r'(\d{2,3})\.' + ext + r'$', url)
            if match and url.startswith(base_url):
                sequential.append(int(match.group(1)))
        
        if len(sequential) < 3:
            return urls  # pattern doesn't match enough URLs
        
        # checking for the page count in HTML( with the common patterns)
        page_indicators = [
            r'<div>(\d+)</div>.*?progress',  # progress bar
            r'"pages?"\s*:\s*(\d+)',  # JSON page count
            r'Page\s+\d+\s+of\s+(\d+)',  # "Page 1 of 11"
            r'(\d+)\s+pages?',  # "11 pages"
        ]
        
        max_page = max(sequential)
        for pattern in page_indicators:
            match = re.search(pattern, html, re.I)
            if match:
                detected_count = int(match.group(1))
                if detected_count > max_page and detected_count < 200:
                    max_page = detected_count
                    self.log_message(f"Detected {detected_count} total pages (completing lazy-loaded URLs...)", "info")
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
            match = re.search(r'(\d{2,3})\.' + ext + r'$', url)
            return int(match.group(1)) if match else 9999
        
        return sorted(completed, key=get_num)

    def generate_cbz(self, output_dir: Path, image_paths: list):
        try:
            cbz_path = output_dir / f"{output_dir.name}.cbz"
            with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for img_path in sorted(image_paths):
                    # Soooo cbz breaks from webp image idk why, so i just added a convert to JPG
                    if self.convert_webp_cbz_var.get() and img_path.suffix.lower() == '.webp' and PIL_AVAILABLE:
                        try:
                            from PIL import Image as PILImage
                            img = PILImage.open(img_path)
                            
                            if img.mode in ('RGBA', 'LA', 'P'):
                                background = PILImage.new('RGB', img.size, (255, 255, 255))
                                if img.mode == 'P':
                                    img = img.convert('RGBA')
                                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = background
                            elif img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            jpg_name = img_path.stem + ".jpg"
                            
                            # (big brain move :p))
                            jpg_buffer = io.BytesIO()
                            img.save(jpg_buffer, format='JPEG', quality=95, optimize=True)
                            jpg_buffer.seek(0)
                            zf.writestr(jpg_name, jpg_buffer.read())
                            self.log_message(f"  Converted {img_path.name} → {jpg_name}", "info")
                        except Exception as e:
                            # Conversion failed, so just add the original (we YOLO this)
                            zf.write(img_path, img_path.name)
                            self.log_message(f"  Couldn't convert {img_path.name}, added as-is", "warn")
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
                [p for p in output_dir.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')],
                key=lambda x: int(re.search(r'(\d+)', x.stem).group(1)) if re.search(r'(\d+)', x.stem) else 0
            )
            if not images:
                raise ValueError("No images found for PDF generation")

            imgs = [Image.open(p).convert("RGB") for p in images]
            pdf_path = output_dir / f"{output_dir.name}.pdf"
            imgs[0].save(pdf_path, "PDF", resolution=100.0, save_all=True, append_images=imgs[1:])
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
