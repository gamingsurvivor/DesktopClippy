import random
import tkinter as tk
import threading
import os
import time
from google import genai
from google.genai import types
from PIL import Image, ImageTk, ImageSequence

# --- Configuration & State ---
current_x = 500  
cycle = 0
check = 8  # Starts with appear
event_number = 1 

# New Global Variables for Timers and Interrupts
last_action_time = time.time()
current_after_id = None 

# Ensure this path is correct for your machine
impath = r'C:\Users\gamin\Documents\Desktop clippy'

# --- Window Setup ---
window = tk.Tk()
window.config(highlightbackground='black')
label = tk.Label(window, bd=0, bg='black')
window.overrideredirect(True)
window.wm_attributes('-transparentcolor', 'black')
window.attributes('-topmost', True) 
label.pack()

# --- Asset Loading ---
def load_gif(name):
    frames = []
    filepath = os.path.join(impath, f'{name}.gif')
    if not os.path.exists(filepath):
        print(f"WARNING: File missing -> {filepath}")
        return frames
        
    try:
        img = Image.open(filepath)
        for frame in ImageSequence.Iterator(img):
            clean_frame = frame.copy().convert("RGBA")
            frames.append(ImageTk.PhotoImage(clean_frame))
    except Exception as e:
        print(f"WARNING: Could not load {name}.gif. Error: {e}")
    return frames

idle = load_gif('idle')
idle2 = load_gif('idle2')
sleep = load_gif('sleeping')
sleep2 = load_gif('sleeping2')
appear = load_gif('appear')
disappear = load_gif('disappear')
thinking = load_gif('thinking')
writing = load_gif('writing')
done = load_gif('done')
reading = load_gif('reading')

# --- State Interrupt System ---

def change_state(new_state):
    """ Instantly overwrites the current animation with a new one! """
    global check, cycle, last_action_time, current_after_id, event_number
    
    check = new_state
    cycle = 0
    last_action_time = time.time() # Reset the sleep timer!
    
    # Pick random variations for idle/sleep when changing to them
    if check == 0: event_number = random.choice([1, 2])
    elif check == 1: event_number = random.choice([3, 4])
    
    # Cancel the current pending frame so there is zero delay
    if current_after_id is not None:
        window.after_cancel(current_after_id)
        current_after_id = None
        
    update() # Force the new frame to draw immediately

# --- Main Animation Loop ---

def update():
    global cycle, check, event_number, current_x, last_action_time, current_after_id

    # 1. Check Sleep Timer (If idle for 15 seconds -> go to sleep!)
    if check == 0 and (time.time() - last_action_time > 15):
        check = 1
        cycle = 0
        event_number = random.choice([3, 4])

    # 2. Select correct GIF
    if check == 0: frames = idle if event_number == 1 else idle2
    elif check == 1: frames = sleep if event_number == 3 else sleep2
    elif check == 4: frames = thinking
    elif check == 5: frames = reading
    elif check == 6: frames = done
    elif check == 7: frames = writing
    elif check == 8: frames = appear
    elif check == 9: frames = disappear
    else: frames = idle

    if not frames: frames = idle
    if not frames: 
        current_after_id = window.after(100, update)
        return

    if cycle >= len(frames): cycle = 0

    # 3. Draw frame
    frame = frames[cycle]
    current_y = window.winfo_y() if window.winfo_y() > 0 else 500
    window.geometry(f'100x100+{current_x}+{current_y}')
    label.configure(image=frame)

    # 4. Advance cycle
    cycle += 1

    # 5. Handle Transitions when GIF finishes
    if cycle >= len(frames):
        cycle = 0
        if check == 8: 
            change_state(0) # Appear -> Idle
            return
        elif check == 9: 
            window.destroy()
            return
        elif check == 0: 
            event_number = random.choice([1, 2]) # Mix up idle animations
        elif check == 1:
            event_number = random.choice([3, 4]) # Mix up sleep animations

    # 6. Dynamic Animation Speeds
    delay = 100
    if check == 0: delay = 300       
    elif check == 1: delay = 800     
    elif check == 4: delay = 150     

    # Save the ID so we can cancel it if the user clicks!
    current_after_id = window.after(delay, update)

# --- Chat & API Logic ---

def inputBox():
    change_state(7) # Instantly trigger writing
    
    dialog = tk.Toplevel(window)
    dialog.geometry("300x70")
    dialog.protocol("WM_DELETE_WINDOW", lambda: [dialog.destroy(), change_state(0)])

    frame = tk.Frame(dialog, bg='#42c2f4', bd=5)
    frame.place(relwidth=1, relheight=1)
    
    entry = tk.Entry(frame, font=30)
    entry.place(relwidth=0.65, rely=0.02, relheight=0.96)
    entry.focus_set()

    submit = tk.Button(frame, text='Ask', command=lambda: handle_submit(entry.get(), dialog))
    submit.place(relx=0.7, rely=0.02, relheight=0.96, relwidth=0.3)
    dialog.bind('<Return>', lambda e: handle_submit(entry.get(), dialog))

def handle_submit(prompt, dialog):
    dialog.destroy()
    change_state(4) # Instantly trigger thinking
    show_speech_bubble("Thinking...")
    threading.Thread(target=call_gemini, args=(prompt,), daemon=True).start()

def call_gemini(prompt):
    # ----------------------------------------------------
    client = genai.Client(api_key="")
    # ----------------------------------------------------
    
    try:
        responseAI = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a helpful, nostalgic, and slightly sarcastic 1990s desktop assistant. Keep answers brief."
            )
        )
        
        # We use window.after to safely trigger state changes from the background thread
        window.after(0, change_state, 6) # Done
        time.sleep(1.5) 
        
        window.after(0, change_state, 5) # Reading
        window.after(0, show_speech_bubble, responseAI.text)
        time.sleep(5)
        
        window.after(0, change_state, 0) # Back to Idle
        
    except Exception as e:
        window.after(0, change_state, 0)
        error_text = str(e)[:100] 
        window.after(0, show_speech_bubble, f"Error: {error_text}")

def show_speech_bubble(text):
    if hasattr(show_speech_bubble, "current_bubble") and show_speech_bubble.current_bubble.winfo_exists():
        show_speech_bubble.current_bubble.destroy()

    bubble = tk.Toplevel(window)
    show_speech_bubble.current_bubble = bubble
    bubble.overrideredirect(True)
    bubble.attributes('-topmost', True)
    
    bubble_x = current_x + 90
    bubble_y = window.winfo_y() - 50 if window.winfo_y() > 50 else 500
    bubble.geometry(f"+{bubble_x}+{bubble_y}")

    lbl = tk.Label(bubble, text=text, bg='#FFFFCC', wraplength=200, relief='solid', bd=1, padx=10, pady=10)
    lbl.pack()
    lbl.bind("<Button-1>", lambda e: bubble.destroy())
    bubble.after(15000, bubble.destroy)

# --- Smart Mouse Controls ---

def start_drag(event):
    global last_action_time
    last_action_time = time.time() # Resets timer so picking him up wakes him up!
    if check == 1: # If he is sleeping...
        change_state(0) # Instantly wake him up!
        
    window.start_x = event.x
    window.start_y = event.y
    window.is_dragging = False 

def drag(event):
    if abs(event.x - window.start_x) > 3 or abs(event.y - window.start_y) > 3:
        window.is_dragging = True
        x = window.winfo_x() - window.start_x + event.x
        y = window.winfo_y() - window.start_y + event.y
        window.geometry(f"+{x}+{y}")
        global current_x
        current_x = x

def on_release(event):
    if getattr(window, 'is_dragging', False) == False:
        inputBox()

def quit_clippy(event=None):
    change_state(9) # Instantly trigger disappear

# Smart Left-Click System
label.bind("<ButtonPress-1>", start_drag)
label.bind("<B1-Motion>", drag)
label.bind("<ButtonRelease-1>", on_release)

# Right-Click System
label.bind("<Button-3>", quit_clippy) 

# Start the loop
update() # Starts the chain without delay
window.mainloop()