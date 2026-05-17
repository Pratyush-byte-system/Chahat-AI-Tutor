import subprocess
import os
import sys

# ── App aliases for Windows ────────────────────────────────
WIN_APP_ALIASES = {
    "chrome":                "chrome",
    "google chrome":         "chrome",
    "firefox":               "firefox",
    "edge":                  "msedge",
    "microsoft edge":        "msedge",
    "brave":                 "brave",
    "notepad":               "notepad",
    "notepad++":             "notepad++",
    "calculator":            "calc",
    "calc":                  "calc",
    "cmd":                   "cmd",
    "command prompt":        "cmd",
    "terminal":              "wt",
    "task manager":          "taskmgr",
    "explorer":              "explorer",
    "file explorer":         "explorer",
    "paint":                 "mspaint",
    "settings":              "ms-settings:",
    "vscode":                "code",
    "vs code":               "code",
    "visual studio code":    "code",
    "whatsapp":              "shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
    "spotify":               "shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify",
    "vlc":                   "vlc",
    "obs":                   "obs64"
}

# ── App aliases for macOS ──────────────────────────────────
MAC_APP_ALIASES = {
    "chrome":                "Google Chrome",
    "google chrome":         "Google Chrome",
    "firefox":               "Firefox",
    "safari":                "Safari",
    "edge":                  "Microsoft Edge",
    "microsoft edge":        "Microsoft Edge",
    "brave":                 "Brave Browser",
    "notepad":               "TextEdit",
    "textedit":              "TextEdit",
    "calculator":            "Calculator",
    "calc":                  "Calculator",
    "terminal":              "Terminal",
    "cmd":                   "Terminal",
    "command prompt":        "Terminal",
    "activity monitor":      "Activity Monitor",
    "task manager":          "Activity Monitor",
    "finder":                "Finder",
    "explorer":              "Finder",
    "file explorer":         "Finder",
    "system preferences":    "System Settings",
    "settings":              "System Settings",
    "vscode":                "Visual Studio Code",
    "vs code":               "Visual Studio Code",
    "visual studio code":    "Visual Studio Code",
    "whatsapp":              "WhatsApp",
    "spotify":               "Spotify",
    "vlc":                   "VLC",
    "obs":                   "OBS",
    "music":                 "Music",
    "apple music":           "Music"
}

# Unified aliases dictionary based on OS
APP_ALIASES = MAC_APP_ALIASES if sys.platform == "darwin" else WIN_APP_ALIASES

UWP_PREFIXES = ["shell:AppsFolder\\", "ms-settings:", "shell:"]
PS = r"C:\Windows\System32\windowsPowerShell\v1.0\powershell.exe"

def is_uwp(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in UWP_PREFIXES)

def open_app(app_name: str) -> str:
    name = app_name.lower().strip()

    search = APP_ALIASES.get(name)
    if not search:
        for key, value in APP_ALIASES.items():
            if name in key or key in name:
                search = value
                break
    
    if not search:
        search = name
        
    print(f"opening: '{search}' (requested as '{app_name}')")
    
    # ── macOS Implementation ──
    if sys.platform == "darwin":
        try:
            # -a lets us pass the app name (e.g. "Google Chrome")
            subprocess.Popen(["open", "-a", search])
            return f"हाँ जान, {app_name} अभी खोलती हूँ! ❤️"
        except Exception as e:
            print("Mac direct launch failed...", e)
            try:
                # fallback for raw paths or urls
                subprocess.Popen(["open", search])
                return f"हाँ जान, {app_name} अभी खोलती हूँ! ❤️"
            except Exception as e2:
                print("All Mac launch methods failed...", e2)
                return f"माफ करना जान, मैं {app_name} नहीं खोल पा रही हूँ 😔 शायद ये app मेरे लिए बहुत मुश्किल है... 💕"

    # ── Windows Implementation ──
    if is_uwp(search):
        try:
            subprocess.Popen([PS, "-NoProfile", "-WindowStyle", "Hidden", "-Command", f"Start-Process '{search}'"], 
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            return f"हाँ जान, {app_name} अभी खोलती हूँ! ❤️"
        except Exception as e:
            print("UWP method failed, trying direct launch...", e)

    try:
        subprocess.Popen(["cmd", "/c", "start", "", search], shell=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return f"हाँ जान, {app_name} अभी खोलती हूँ! ❤️"
    except Exception as e1:
        print("Direct launch failed, trying shell=True...", e1)
        try:
            subprocess.Popen(search, shell=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            return f"हाँ जान, {app_name} अभी खोलती हूँ! ❤️"
        except Exception as e2:
            print("All conventional methods failed...", e2)
            try:
                cmd = f"(Get-AppxPackage -Name *{search}*).PackageFamilyName"
                r = subprocess.run([PS, "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=8)
                package_family = r.stdout.strip()
                if package_family:
                    cmd_app_id = f"(Get-AppxPackageManifest (Get-AppxPackage -Name '{package_family}')).Package.Applications.Application.Id"
                    r_id = subprocess.run([PS, "-NoProfile", "-Command", cmd_app_id], capture_output=True, text=True, timeout=5)
                    app_id = r_id.stdout.strip()
                    if app_id:
                        full_id = f"{package_family}!{app_id}"
                        subprocess.Popen([PS, "-NoProfile", "-WindowStyle", "Hidden", "-Command", f"Start-Process 'shell:AppsFolder\\{full_id}'"], 
                                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                        return f"हाँ जान, {app_name} अभी खोलती हूँ! ❤️"
            except Exception as e3:
                print("UWP lookup method failed...", e3)
            
            return f"माफ करना जान, मैं {app_name} नहीं खोल पा रही हूँ 😔 शायद ये app मेरे लिए बहुत मुश्किल है... 💕"

if __name__ == "__main__":
    # Test cases
    print(open_app("notepad"))
    print(open_app("whatsapp"))
