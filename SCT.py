import threading
import logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from playwright.sync_api import sync_playwright, TimeoutError

# =========================
# LOGGING
# =========================
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    filename=f"logs/security_run_{ts}.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log(msg, level="info"):
    if level == "error":
        logging.error(msg)
    else:
        logging.info(msg)
    app.log_to_ui(msg)


# =========================
# SECURITY ENGINE
# =========================
LOGIN_PATH = "/mobiledoc/jsp/webemr/login/newLogin.jsp"
CLOUD_DOMAIN = "ecwcloud.in"
LABS_DOMAIN = "ecwlabs.in"


def build_urls(practice_code):
    return [
        f"https://{practice_code}.{CLOUD_DOMAIN}{LOGIN_PATH}",
        f"https://{practice_code}.{LABS_DOMAIN}{LOGIN_PATH}"
    ]


def is_login_page(page):
    try:
        page.wait_for_selector("text=Enter username to continue", timeout=5000)
        return True
    except TimeoutError:
        return False


def login(page, username, password):
    log("Attempting login...")
    page.get_by_role("textbox", name="Enter username to continue").fill(username)
    page.get_by_role("button", name="Next").click()
    page.get_by_role("textbox", name="Enter Password to continue").fill(password)
    page.get_by_role("button", name="Log In").click()
    page.wait_for_load_state("networkidle")
    log("Login successful")


def get_logged_in_profile_name(page):
    log("Detecting logged-in profile name...")
    selectors = [
        "#providerLicense",
        ".user-name",
        ".profile-name"
    ]
    for sel in selectors:
        try:
            txt = page.locator(sel).inner_text().strip()
            if "," in txt:
                log(f"Profile detected: {txt}")
                return txt
        except:
            pass
    raise Exception("Unable to detect profile name")


def check_server_version(page):
    log("Checking Server Version...")
    page.get_by_text("Menu", exact=True).click()
    page.locator("#pane11").get_by_text("Help").click()
    page.get_by_text("About eClinicalWorks", exact=True).click()
    version_text = page.get_by_text("Server Version:").inner_text()
    log(f"Server Version: {version_text}")
    page.locator("#aboutEcw").get_by_text("×").click()


def jellybean_message_test(page, profile_name):
    log("Running Jellybean Union All test...")
    page.get_by_role("link", name="Inbox").click()
    page.get_by_role("button", name=" Compose Message").click()

    page.get_by_role("textbox", name="Recipients").click()
    page.get_by_role("textbox", name="Recipients").fill(profile_name[:3])
    page.get_by_text(profile_name).click()

    page.get_by_role("textbox", name="Subject").fill("Filter Test")

    iframe = page.locator("#compose iframe").content_frame
    iframe.locator("body").fill("union all")

    page.get_by_role("button", name="Send").click()
    log("Message sent")

    page.wait_for_timeout(3000)
    page.get_by_role("link", name="Inbox").click()

    latest = page.locator("[id^=message_]").first
    latest.click()

    body = page.locator("#messageDetails").inner_text()
    if "union all" in body.lower():
        log("Union All filter test PASSED")
    else:
        log("Union All filter test FAILED", "error")


def run_security_flow(practice_codes, username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        active = None

        # Step 1: Try practice codes
        for code in practice_codes:
            log(f"Trying practice code: {code}")
            for url in build_urls(code):
                try:
                    log(f"Opening {url}")
                    page.goto(url, timeout=15000)
                    if is_login_page(page):
                        log(f"Valid login page found: {url}")
                        active = url
                        break
                except:
                    log(f"Failed loading {url}", "error")
            if active:
                break

        if not active:
            log("No valid practice code found. Stopping.", "error")
            browser.close()
            return

        # Step 2: Login
        login(page, username, password)

        # Step 3: Profile name
        profile_name = get_logged_in_profile_name(page)

        # Step 4: Server version
        check_server_version(page)

        # Step 5: Jellybean test
        jellybean_message_test(page, profile_name)

        log("Security Control Test Completed")
        context.close()
        browser.close()


# =========================
# TKINTER UI
# =========================
class SecurityApp:
    def __init__(self, root):
        self.root = root
        root.title("Security Control Test Utility")
        root.geometry("900x600")
        root.configure(bg="#1e1e1e")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#1e1e1e", foreground="white")
        style.configure("TButton", background="#007acc", foreground="white")
        style.configure("TEntry", fieldbackground="#2d2d2d", foreground="white")

        ttk.Label(root, text="Practice Codes (comma separated)").pack(pady=5)
        self.practice_entry = ttk.Entry(root, width=60)
        self.practice_entry.pack()

        ttk.Label(root, text="Username").pack(pady=5)
        self.username_entry = ttk.Entry(root, width=40)
        self.username_entry.pack()

        ttk.Label(root, text="Password").pack(pady=5)
        self.password_entry = ttk.Entry(root, width=40, show="*")
        self.password_entry.pack()

        self.start_btn = ttk.Button(root, text="Start Security Test", command=self.start_test)
        self.start_btn.pack(pady=10)

        ttk.Label(root, text="Live Logs").pack()
        self.log_box = scrolledtext.ScrolledText(root, height=20, bg="#111", fg="lime")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def log_to_ui(self, message):
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.root.update()

    def start_test(self):
        pcodes = self.practice_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not pcodes or not username or not password:
            messagebox.showerror("Error", "All fields are required")
            return

        practice_codes = [p.strip() for p in pcodes.split(",")]

        self.log_box.delete("1.0", tk.END)
        self.log_to_ui("Starting Security Control Test...\n")

        thread = threading.Thread(
            target=run_security_flow,
            args=(practice_codes, username, password),
            daemon=True
        )
        thread.start()


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    root = tk.Tk()
    app = SecurityApp(root)
    root.mainloop()
