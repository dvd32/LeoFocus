import json
import time
import threading
import os
import sys
from pynput import keyboard, mouse
import subprocess
from collections import Counter
from local_summarizer import get_start_session_advice
from llm_client import create_json_memory, generate_final_report_from_memory

# FORCE UTF-8 ON WINDOWS
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ============================================
# CROSS-PLATFORM POPUP SCRIPT (The "Blueprint")
# ============================================
POPUP_SCRIPT_CODE = r"""
import tkinter as tk
import sys
import os

def show_popup(app_name, img_path):
    try:
        root = tk.Tk()
        root.title("Leonardo is Displeased")

        # --- THEME ---
        bg_color = "#FAF8F5"
        text_color = "#1A1614"
        accent_color = "#B8442C"
        btn_bg = "#1A1614" 

        # --- SETUP HIDDEN WINDOW ---
        # Hide window initially to prevent 'jumping' or wrong placement
        root.withdraw()

        # --- GEOMETRY CALCULATION ---
        w, h = 420, 520
        
        # Get screen dimensions
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        
        # Calculate X and Y coordinates (Strict Integers)
        x = int((ws / 2) - (w / 2))
        y = int((hs / 2) - (h / 2))
        
        # Set position
        root.geometry(f'{w}x{h}+{x}+{y}')

        # --- OS SPECIFIC TWEAKS ---
        root.configure(bg=accent_color)
        root.attributes("-topmost", True)
        
        # Borderless logic (Safe for all platforms)
        try:
            root.overrideredirect(True) 
        except:
            pass

        # --- CLOSE LOGIC ---
        def close_popup(event=None):
            root.destroy()
        
        root.bind("<Escape>", close_popup)
        root.bind("<Button-1>", close_popup)

        # --- CONTENT ---
        inner_frame = tk.Frame(root, bg=bg_color)
        inner_frame.pack_propagate(False) 
        inner_frame.pack(expand=True, fill="both", padx=5, pady=5)
        inner_frame.bind("<Button-1>", close_popup)

        # Title
        tk.Label(inner_frame, text="Che disastro!", font=("Times New Roman", 22, "bold italic"), 
                 bg=bg_color, fg=accent_color).pack(pady=(20, 10))

        # Image (With Resize Loop)
        try:
            if os.path.exists(img_path):
                photo = tk.PhotoImage(file=img_path)
                # Auto-shrink logic
                while photo.width() > 220 or photo.height() > 220:
                    photo = photo.subsample(2, 2)
                img_lbl = tk.Label(inner_frame, image=photo, bg=bg_color)
                img_lbl.image = photo
                img_lbl.pack(pady=5)
                img_lbl.bind("<Button-1>", close_popup)
            else:
                tk.Label(inner_frame, text="😡", font=("Arial", 50), bg=bg_color).pack(pady=10)
        except Exception:
            tk.Label(inner_frame, text="😡", font=("Arial", 50), bg=bg_color).pack(pady=10)

        # Message
        msg_text = (f"You dare waste your genius on\n{app_name}?\n\n"
                    f"I did not paint the Mona Lisa\nwhile distracted by such nonsense.")
        
        msg_lbl = tk.Label(inner_frame, text=msg_text, font=("Garamond", 15), 
                 bg=bg_color, fg=text_color, justify="center")
        msg_lbl.pack(pady=15, padx=10)
        msg_lbl.bind("<Button-1>", close_popup)

        # --- CUSTOM FAKE BUTTON (For High Contrast) ---
        btn = tk.Label(inner_frame, 
                       text="I SHALL FOCUS NOW", 
                       font=("Helvetica", 11, "bold"),
                       bg=btn_bg, 
                       fg="white",
                       padx=20, 
                       pady=12,
                       cursor="hand2")
        
        btn.pack(side="bottom", pady=25)
        btn.bind("<Button-1>", close_popup)

        # --- SHOW WINDOW ---
        # Reveal the window now that it is positioned correctly
        root.deiconify()

        # --- FORCE FOCUS (CRITICAL FOR MAC) ---
        root.lift()
        root.focus_force()
        
        # Mac-specific: Force window to front using AppleScript
        if sys.platform == "darwin":
            try:
                os.system('''/usr/bin/osascript -e 'tell app "System Events" to set frontmost of first process whose unix id is %d to true' ''' % os.getpid())
            except:
                pass

        root.mainloop()

    except Exception as e:
        print(f"Popup error: {e}")

if __name__ == "__main__":
    try:
        app = sys.argv[1] if len(sys.argv) > 1 else "Distraction"
        img = sys.argv[2] if len(sys.argv) > 2 else ""
        show_popup(app, img)
    except:
        pass
"""

# -----------------------------
# Apllication Configuration
# -----------------------------
DISTRACTING_APPS = ["YouTube", "TikTok", "Netflix", "Facebook", "Instagram", "WhatsApp", "TV"]
PRODUCTIVE_APPS = ["VSCode", "PyCharm", "Terminal", "Word", "Excel", "Electron", "GitHub", "GitHub Desktop", "Notes", "Note", "Obsidian", "Notion", "Sublime Text", "IntelliJ IDEA", "Xcode", "Android Studio"]
BROWSER_DISTRACTIONS = ["Facebook", "Instagram", "Netflix", "YouTube", "TikTok", "Reddit", "Twitter", "Prime Video", "Twitch", "Spotify"]
STOP_REQUESTED = False

# SYSTEM PROCESSES TO IGNORE (Windows)
SYSTEM_PROCESSES = [
    "Program Manager",
    "Realtek Audio Console",
    "OmApSvcBroker",
    "Experiencia de entrada de Windows",
    "NVIDIA GeForce Overlay",
    "NVIDIA Share",
    "Windows Shell Experience Host",
    "Microsoft Text Input Application",
    "SearchUI",
    "ShellExperienceHost",
    "ApplicationFrameHost",
    "TextInputHost",
    "Settings",
    "Configuración",
    "SystemSettings",
    "Windows Security",
    "Seguridad de Windows",
    "Conmutación de tareas",   # (Spanish)
    "Task Switching",          # (English)
    "Task View"                # (Windows 10/11)
]

# SYSTEM PROCESSES TO IGNORE (macOS)
MAC_SYSTEM_PROCESSES = [
    "Dock",
    "Finder",
    "SystemUIServer",
    "Control Center",
    "NotificationCenter",
    "loginwindow",
    "WindowServer"
]

# -----------------------------
# GLOBAL STATE
# -----------------------------
activity_state = {
    "key_presses": 0,
    "mouse_moves": 0,
    "mouse_clicks": 0,
    "active_window": None,
    "last_window": None,
    "window_switches": 0,
    "last_switch_time": time.time(),
    "window_times": {},
    "session_start": time.time(),
    "last_input_time": time.time(),
    "inactive_threshold": 10,
    "session_end": None,
    "pause_periods": [],
    "last_pause_start": None,
    "total_distracted_time" : 0
}

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def is_system_process(window_name):
    """Check if a window is a system process that should be ignored"""
    if not window_name:
        return True
    
    # Check Windows system processes
    for system_proc in SYSTEM_PROCESSES:
        if system_proc.lower() in window_name.lower():
            return True
    
    # Check macOS system processes
    for system_proc in MAC_SYSTEM_PROCESSES:
        if system_proc.lower() in window_name.lower():
            return True
    
    # Ignore very short names (likely system processes)
    if len(window_name.strip()) < 2:
        return True
    
    # Ignore windows with sharing notifications
    if "compartiendo tu pantalla" in window_name.lower():
        return True
    if "is sharing your screen" in window_name.lower():
        return True
    
    return False

# -----------------------------
# ACTIVE WINDOW DETECTION
# -----------------------------
def get_active_window():
    try:
        if sys.platform == "darwin":
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            active_app = subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
            return active_app if not is_system_process(active_app) else None
        else:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win and win.title:
                return str(win.title) if not is_system_process(win.title) else None
            return None
    except:
        return None

# -----------------------------
# DOCUMENT / TAB NAMES
# -----------------------------
def get_document_name(window_name):
    if not window_name:
        return ""

    if sys.platform == "darwin":
        try:
            if "Word" in window_name:
                script = 'tell application "Microsoft Word" to get name of active document'
                return subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
            if "Excel" in window_name:
                script = 'tell application "Microsoft Excel" to get name of active workbook'
                return subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
            if "Safari" in window_name:
                script = 'tell application "Safari" to get name of front document'
                return subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
            if "Chrome" in window_name:
                script = 'tell application "Google Chrome" to get title of active tab of front window'
                return subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
            if "Firefox" in window_name:
                if " — " in window_name:
                    return window_name.split(" — ")[0]
                return window_name
            if "Edge" in window_name:
                script = 'tell application "Microsoft Edge" to get title of active tab of front window'
                return subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
        except:
            return window_name

        if " — " in window_name:
            return window_name.split(" — ")[0]
        if " | " in window_name:
            return window_name.split(" | ")[0]

        return window_name

    else:  # Windows
        try:
            import win32com.client
            if "Word" in window_name:
                word = win32com.client.Dispatch("Word.Application")
                if word.Documents.Count > 0:
                    return word.ActiveDocument.Name
            elif "Excel" in window_name:
                excel = win32com.client.Dispatch("Excel.Application")
                if excel.Workbooks.Count > 0:
                    return excel.ActiveWorkbook.Name
            elif "PowerPoint" in window_name:
                ppt = win32com.client.Dispatch("PowerPoint.Application")
                if ppt.Presentations.Count > 0:
                    return ppt.ActivePresentation.Name
        except:
            pass

        # browser heuristics
        if any(browser in window_name for browser in ["Chrome", "Firefox", "Edge"]):
            if " - " in window_name:
                return window_name.split(" - ")[0]
            if " | " in window_name:
                return window_name.split(" | ")[0]

        # IDE/other apps
        if " — " in window_name:
            return window_name.split(" — ")[0]

        return window_name


# -----------------------------
# MONITOR WINDOW
# -----------------------------
def monitor_active_window():
    while True:
        current = get_active_window()
        now = time.time()
        last = activity_state["last_window"]

        # Pause detection
        inactive_elapsed = now - activity_state["last_input_time"]
        
        # Start pause if inactive for too long
        if inactive_elapsed > activity_state["inactive_threshold"]:
            if activity_state["last_pause_start"] is None:
                activity_state["last_pause_start"] = activity_state["last_input_time"]
                print(f"Pause started at {time.ctime(activity_state['last_pause_start'])}")
        else:
            # End pause when activity resumes
            if activity_state["last_pause_start"] is not None:
                pause_end = now
                pause_duration = pause_end - activity_state["last_pause_start"]
                activity_state["pause_periods"].append({
                    "start": time.ctime(activity_state["last_pause_start"]),
                    "end": time.ctime(pause_end),
                    "duration": int(pause_duration)
                })
                print(f"Pause ended. Duration: {int(pause_duration)} seconds")
                activity_state["last_pause_start"] = None

        # Window switching logic
        if current != last:
            if last:
                elapsed = now - activity_state["last_switch_time"]
                activity_state["window_times"][last] = activity_state["window_times"].get(last, 0) + elapsed

            activity_state["window_switches"] += 1
            activity_state["active_window"] = current
            activity_state["last_window"] = current
            activity_state["last_switch_time"] = now

        time.sleep(0.5)

# -----------------------------
# KEYBOARD & MOUSE
# -----------------------------
def on_key_press(key):
    activity_state["key_presses"] += 1
    activity_state["last_input_time"] = time.time()

def on_move(x, y):
    activity_state["mouse_moves"] += 1
    activity_state["last_input_time"] = time.time()

def on_click(x, y, button, pressed):
    if pressed:
        activity_state["mouse_clicks"] += 1
        activity_state["last_input_time"] = time.time()

def on_scroll(x, y, dx, dy):
    activity_state["last_input_time"] = time.time()

# ============================================
# SUBPROCESS POPUP LAUNCHER (Safe for Mac/Linux)
# ============================================
last_scold_time = 0

def show_da_vinci_scolding(distraction_name):
    """
    Launches a completely separate python process to show the popup.
    This prevents 'Main Thread' crashes on macOS and Linux.
    """
    
    # 1. Clean up app name
    clean_name = distraction_name
    for app in DISTRACTING_APPS + BROWSER_DISTRACTIONS:
        if app.lower() in distraction_name.lower():
            clean_name = app
            break
    
    # 2. Prepare paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(script_dir, "angry.png")
    
    # 3. Launch the popup in a new independent process
    try:
        # We pass the python code string directly to the new process using "-c"
        subprocess.Popen(
            [sys.executable, "-c", POPUP_SCRIPT_CODE, clean_name, img_path],
            stdout=subprocess.DEVNULL, # Hide output
            stderr=subprocess.DEVNULL, # Hide errors
            start_new_session=True     # Detach completely (Linux/Mac)
        )
    except Exception as e:
        print(f"Failed to launch popup subprocess: {e}")


# -----------------------------
# REPORT LOOP
# -----------------------------
def report_loop_json():
    # Initial State of the memory
    memory_context = {
        "focus_score": 100,
        "status": "Starting",
        "user_role": activity_state.get("user_context", "General Creator"),
        "summary_so_far": "Session started.",
        "leonardo_comment": "I am observing.",
        "history": []
    }
    
    activity_state["memory_context"] = memory_context
    last_chunk_time = time.time()
    
    chunk_windows_list = []      
    chunk_distraction_hits = 0   
    chunk_samples = 0            

    while not STOP_REQUESTED:
        time.sleep(1)
        now = time.time()
        
        app_name = activity_state["active_window"]
        doc_name = ""
        
        if app_name:
            doc_name = get_document_name(app_name)
            elapsed = now - activity_state["last_switch_time"]
            activity_state["window_times"][app_name] = activity_state["window_times"].get(app_name, 0) + elapsed
            activity_state["last_switch_time"] = now

        # 1. RILEVAMENTO DISTRAZIONI PIÙ INTELLIGENTE
        is_distracted_now = False
        full_window_name = app_name if app_name else "Idle"
        
        if app_name:
            if doc_name:
                full_window_name = f"{app_name} ({doc_name})"
            
            # FIX: Controllo se una delle app vietate è CONTENUTA nel nome (non match esatto)
            # Es. "WhatsApp" in "(1) WhatsApp" -> True
            is_distracted_by_app = any(d_app.lower() in app_name.lower() for d_app in DISTRACTING_APPS)
            
            if is_distracted_by_app:
                is_distracted_now = True
            
            # Check Browser
            elif app_name in ["Google Chrome", "Safari", "Firefox", "Microsoft Edge", "Arc"]:
                for distractor in BROWSER_DISTRACTIONS:
                    if distractor.lower() in doc_name.lower():
                        is_distracted_now = True
                        break
        
        # Accumula dati
        chunk_samples += 1
        if is_distracted_now:
            chunk_distraction_hits += 1
            activity_state["total_distracted_time"] += 1
        
        if app_name:
            chunk_windows_list.append(full_window_name)

        # Invia dati UI a Flutter
        data_packet = {
            "type": "update",
            "active_window": full_window_name,
            "total_time": int(now - activity_state["session_start"]),
            "switches": activity_state['window_switches'],
            "keys": activity_state['key_presses'],
            "mouse": activity_state['mouse_moves'],
            "is_inactive": (now - activity_state["last_input_time"]) > activity_state["inactive_threshold"],
            "top_apps": sorted(activity_state["window_times"].items(), key=lambda x: x[1], reverse=True)[:5]
        }
        print(json.dumps(data_packet), flush=True)

        # === CHECK EVERY 30 SECONDS ===
        if now - last_chunk_time >= 30:
            
            # Calcolo Percentuali Matematiche
            recent_distraction = 0
            if chunk_samples > 0:
                recent_distraction = int((chunk_distraction_hits / chunk_samples) * 100)

            session_duration = now - activity_state["session_start"]
            global_distraction = 0
            if session_duration > 0:
                global_distraction = int((activity_state["total_distracted_time"] / session_duration) * 100)
            
            unique_windows = list(set(chunk_windows_list))
            
            chunk_data = {
                "windows": unique_windows,
                "duration": 30,
                "recent_distraction": recent_distraction, 
                "global_distraction": global_distraction
            }
            
            try:
                # Chiediamo all'LLM di valutare
                new_memory = create_json_memory(chunk_data, memory_context, activity_state["user_context"])
                
                # --- 2. IL POLIZIOTTO CATTIVO (MATH OVERRIDE) ---
                # Se l'LLM è troppo gentile, correggiamo noi il voto.
                # Regola: Il focus score non può essere superiore a (100 - % distrazione recente)
                max_allowed_score = 100 - recent_distraction
                
                # Bonus di tolleranza: diamo +10 punti extra se non è 100% distrazione, ma non oltre 100
                if recent_distraction < 100:
                    max_allowed_score += 10 
                
                llm_score = new_memory.get('focus_score', 50)
                
                # Applichiamo la correzione se l'LLM ha dato voti troppo alti
                if llm_score > max_allowed_score:
                    # Se l'LLM dice 90 ma tu eri su WhatsApp (90% distr), max_allowed è 20.
                    # Riscriviamo lo score brutale.
                    new_memory['focus_score'] = max_allowed_score
                    new_memory['leonardo_comment'] = "I see your distraction clearly. Do not deceive yourself." # Forziamo un commento severo se serve
                
                # -----------------------------------------------

                if 'history' not in new_memory:
                    new_memory['history'] = memory_context.get('history', [])
                
                history_entry = {
                    "iteration": len(new_memory['history']) + 1,
                    "timestamp": now,
                    "score": new_memory.get('focus_score', 50),
                    "windows": unique_windows,
                    "recent_distraction": recent_distraction,
                    "global_distraction": global_distraction,
                    "duration": 30
                }
                new_memory['history'].append(history_entry)
                
                if len(new_memory['history']) > 50:
                    new_memory['history'] = new_memory['history'][-50:]
                
                memory_context = new_memory
                activity_state["memory_context"] = memory_context 
                
                # Determina emozione basata sui DATI REALI, non sull'LLM.
                # Solo 'angry' e 'happy' hanno un asset in running_view.dart:
                # ogni altro valore ricadrebbe comunque nel default neutro.
                current_emotion = 'neutral'
                current_score = memory_context.get('focus_score', 100)
                
                global last_scold_time # Access the global timer
                
                if recent_distraction > 50:
                    current_emotion = 'angry'
                    
                    # --- SMARTER POPUP TRIGGER ---
                    if (now - last_scold_time) > 60:
                        
                        # 1. Count which windows were used in this "angry" chunk
                        # chunk_windows_list contains the active window for every second of the last 30s
                        window_counts = Counter(chunk_windows_list)
                        
                        # 2. Sort them: most frequent first
                        most_common_windows = window_counts.most_common()
                        
                        # 3. Pick the top one that isn't our own app
                        blame_app = "Distraction" # Fallback name
                        
                        for win_name, count in most_common_windows:
                            # IGNORE: leonardoapp, python, or empty names
                            lower_name = win_name.lower()
                            if "leonardoapp" not in lower_name and "python" not in lower_name and "debug" not in lower_name:
                                blame_app = win_name
                                break
                        
                        # 4. Show the popup blaming the real culprit
                        show_da_vinci_scolding(blame_app)
                        last_scold_time = now
                    # -------------------------------

                elif current_score > 85:
                    current_emotion = 'happy'

                leo_packet = {
                    "type": "leo_comment",
                    "content": memory_context.get('leonardo_comment', 'Observing...'),
                    "focus_score": current_score,
                    "emotion": current_emotion # Usiamo l'emozione calcolata da Python
                }
                print(json.dumps(leo_packet), flush=True)
                
            except Exception as e:
                print(f"LLM Error: {e}", file=sys.stderr)

            # Reset
            chunk_windows_list = []
            chunk_distraction_hits = 0
            chunk_samples = 0
            last_chunk_time = now
            
# -----------------------------
# MAIN
# -----------------------------

def _calculate_grade(score):
    """Calculate letter grade from score"""
    if score >= 90:
        return "A+"
    elif score >= 85:
        return "A"
    elif score >= 80:
        return "A-"
    elif score >= 75:
        return "B+"
    elif score >= 70:
        return "B"
    elif score >= 65:
        return "B-"
    elif score >= 60:
        return "C+"
    elif score >= 50:
        return "C"
    else:
        return "D"

def listen_for_commands():
        global STOP_REQUESTED
        while True:
            cmd = sys.stdin.readline().strip()
            if cmd == "STOP":
                STOP_REQUESTED = True
                break

if __name__ == "__main__":
    # 1. ACQUISIZIONE CONTESTO DA ARGOMENTI (passati da Flutter)
    if len(sys.argv) > 1:
        user_context = sys.argv[1]
    else:
        user_context = "General Work Session"

    # --- MAGIC FIX: CONTEXT OVERRIDE ---
    # Rende Leonardo intelligente: se dici che usi WhatsApp, lui non si arrabbia.
    print(f"DEBUG: Analyzing context for exceptions: '{user_context}'")
    context_lower = user_context.lower()

    # 1. Controllo App Standalone (es. WhatsApp, Spotify)
    # Usiamo list(...) per creare una copia e poter modificare l'originale mentre iteriamo
    for app in list(DISTRACTING_APPS): 
        if app.lower() in context_lower:
            print(f"Context Override: {app} detected in goal. Moving to PRODUCTIVE.")
            DISTRACTING_APPS.remove(app)
            PRODUCTIVE_APPS.append(app)

    # 2. Controllo Browser (es. YouTube, Facebook)
    for site in list(BROWSER_DISTRACTIONS):
        if site.lower() in context_lower:
            print(f"Context Override: {site} allowed in browser.")
            BROWSER_DISTRACTIONS.remove(site)
    # -------------------------------------------------------

    activity_state["user_context"] = user_context

    # --- ADVICE PRE-SESSION ---
    # Una sola chiamata all'LLM, inviata a Flutter sia come commento che come
    # consigli iniziali (sono due pacchetti che la UI consuma separatamente).
    try:
        advice = get_start_session_advice(user_context)

        print(json.dumps({
            "type": "leo_comment",
            "content": advice,
        }), flush=True)

        print(json.dumps({
            "type": "initial_advice",
            "content": advice,
        }), flush=True)

    except Exception as e:
        sys.stderr.write(f"Error getting startup advice: {e}\n")


    # =========================================================================
    # Wait for 'START' signal from Flutter
    # =========================================================================
    while True:
        try:
            line = sys.stdin.readline().strip()
            if line == "START":
                break
            elif line == "STOP":
                sys.exit(0)
        except Exception:
            pass
    # =========================================================================

    threading.Thread(target=listen_for_commands, daemon=True).start()

    # Avvia monitoraggio
    activity_state["session_start"] = time.time()
    
    # Thread separati per input
    threading.Thread(target=monitor_active_window, daemon=True).start()
    keyboard_listener = keyboard.Listener(on_press=on_key_press)
    keyboard_listener.start()
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    mouse_listener.start()

    # Usiamo il loop JSON
    report_loop_json()

    # Session ended cleanly
    activity_state["session_end"] = time.time()

    print(json.dumps({"type": "status", "message": "Leonardo is composing the Codex..."}), flush=True)

    final_memory = activity_state.get("memory_context", {})

    session_duration = activity_state["session_end"] - activity_state["session_start"]
    sorted_apps = sorted(activity_state["window_times"].items(), key=lambda x: x[1], reverse=True)[:5]

    stats_package = {
        "duration_seconds": int(session_duration),
        "total_switches": activity_state["window_switches"],
        "focus_score": final_memory.get("focus_score", 50),
        "top_apps": [{"name": k, "seconds": int(v)} for k, v in sorted_apps],
        "total_distraction_time": activity_state.get("total_distracted_time", 0),
        "pause_count": len(activity_state.get("pause_periods", [])),
        "key_presses": activity_state.get("key_presses", 0),
        "mouse_clicks": activity_state.get("mouse_clicks", 0)
    }

    report_markdown = generate_final_report_from_memory(
        final_memory,
        activity_state["user_context"],
        stats_package
    )

    final_packet = {
        "type": "report",
        "content": report_markdown,
        "stats": stats_package,
        "final_score": final_memory.get("focus_score", 50),
        "grade": _calculate_grade(final_memory.get("focus_score", 50)),
        "total_iterations": len(final_memory.get('history', []))
    }

    print(json.dumps(final_packet), flush=True)
    sys.exit(0)