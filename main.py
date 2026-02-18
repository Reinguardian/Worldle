import json
import random
from tkinter import ttk
import tkinter as tk
import threading
from tkinter import font
import requests
import re
from collections import Counter
from ruslingua import RusLingua
import sys, os

### --- Config ---
WORDNIK_API_KEY= "s4sty6niejwwrzd8i2factjrv2kxubkn7bmef5axnsmrhfu7l"
TEXT_COLOR = "#d0ccc4"
BACKGROUND_COLOR = "#191a1b"
POPUP_BACKGROUND_COLOR = "#28292b"
ENGLISH = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
RUSSIAN = ["ЁЙЦУКЕНГШЩЗХЪ", "ФЫВАПРОЛДЖЭ", "ЯЧСМИТЬБЮ"]

### --- State ---
cyphered_word = ""
current_row = 0
current_col = 0
length = 5
attempts = 6
status = None
language = "English"

### --- Helper Functions ---

def resource_path(path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return path

def auto_advance(event, row, col):
    content = text_boxes[row][col].get()
    if event and not event.keysym not in ["Left","Right"]:
        return
    if len(content) == 1 and content.isalpha() and col < length-1 and len(text_boxes[row][col+1].get()) != 1:
        text_boxes[row][col+1].focus()
        text_boxes[row][col+1].selection_range(0, tk.END)       

def auto_backspace(event, row, col):
    if event.keysym == "BackSpace" and text_boxes[row][col].get() == "" and col > 0:
        text_boxes[row][col-1].delete(0, tk.END)
        text_boxes[row][col-1].focus() 

def validate_letter(P):
    # P is the value after the keypress
    if language.get() == "English":
        return len(P) <= 1 and (bool(re.search('[a-zA-Z]', P)) or P== "")
    else:
        return len(P) <= 1 and (bool(re.search('[а-яА-ЯёЁ]', P)) or P== "")

def prevent_paste(event):
    return "break"

def force_uppercase(P):
    # Always allow the change; uppercase is handled in trace
    return True

def on_change(var):
    # Automatically capitalize
    var.set(var.get().upper())

def close_window():
    root.destroy()

def start_move(event):
    root.x = event.x
    root.y = event.y

def stop_move(event):
    root.x = None
    root.y = None

def on_motion(event):
    dx = event.x - root.x
    dy = event.y - root.y
    x = root.winfo_x() + dx
    y = root.winfo_y() + dy
    root.geometry(f"+{x}+{y}")

def on_focus(row, col):
    global current_row, current_col
    current_row = row
    current_col = col

def button_press(letter_pos, event=None):
    text_boxes[current_row][current_col].insert(tk.INSERT,letter_pos)
    auto_advance(event,current_row,current_col)

def backspace_pressed():
    text_boxes[current_row][current_col].delete(0, tk.END)
    if text_boxes[current_row][current_col].get() == "" and current_col > 0:
        text_boxes[current_row][current_col-1].focus() 

def enable_row(row):
    for box in text_boxes[row]:
        box.config(state="normal")
    text_boxes[row][0].focus()

def disable_row(row):
    for box in text_boxes[row]:
        box.config(state="readonly")
    text_boxes[row][0].focus()

def select_length(index):
    global length
    length = index+2
    for length_button in length_buttons:
        length_button.config(bg="#434d5d")
    length_buttons[index].config(bg="#1844a7")

def select_attempts(index):
    global attempts
    attempts = index+2
    for attempt_button in attempt_buttons:
        attempt_button.config(bg="#434d5d")
    attempt_buttons[index].config(bg="#1844a7")

def color_text_box(row, col, color):
    text_boxes[row][col].config(
        readonlybackground=color,
        highlightbackground=color,
        highlightcolor=color
    )

def color_button(letter_pos, color):
    letter_buttons[letter_pos].config(bg=color)

def fetch_definition():
    global definition

    word_cases = [cyphered_word.lower(), cyphered_word.capitalize(), cyphered_word.upper()]

    if language.get() == "English":
        for word in word_cases:
            try:
                response= requests.get(
                    f"http://api.wordnik.com/v4/word.json/{word}/definitions?api_key={WORDNIK_API_KEY}"
                ).json()
                if response:
                    try:
                        # Remove <> tags
                        definition = re.sub(r"<.*?>", "", response[0]["text"])
                        if definition_button.cget("text") == "Loading definition...":
                            definition_button.config(text=definition, height=definition_button.cget("height")+int(len(definition)/37),wraplength=260)
                            if attempts > 6:
                                aftergame_frame.configure(height=aftergame_frame.cget("height")+7*attempts+14*int(len(definition)/37))
                            else:
                                aftergame_frame.configure(height=aftergame_frame.cget("height")+14*int(len(definition)/37))
                        break 
                    except:
                        definition = "No definition"
            except (KeyError, IndexError):
                definition = "No definition"
                continue
    else:
        for word in word_cases:
            try:
                print(word)
                dictionary = RusLingua()
                definition = dictionary.get_definition(word) 
                if definition:
                    print(definition)
                    match = re.search(r"1\.(.*?)\.", definition)
                    if match:
                        definition = match.group(1)
                    else:
                        match = re.search(r"\.(.*?)\;", definition)
                        if match:
                            definition = match.group(1)
                        else:
                            definition = "No definition"
                else:
                    definition = "No definition"
            except (KeyError, IndexError):
                # definition = "No definition"
                continue

def hide_after_game_on_click(event):
    # Check if click was outside the frame
    x, y = event.x_root, event.y_root
    fx, fy = aftergame_frame.winfo_rootx(), aftergame_frame.winfo_rooty()
    fw, fh = aftergame_frame.winfo_width(), aftergame_frame.winfo_height()
    
    if not (fx <= x <= fx + fw and fy <= y <= fy + fh):
        aftergame_frame.place_forget()

### --- Game Logic ---

def play_game(event=None):
    # declare global variables
    global current_row, current_col, status, cyphered_word, definition, length, attempts, text_boxes, language, enter_button, letter_button, letter_buttons
    
    # Reset state variables
    current_row = 0
    current_col = 0
    status = None
    definition = None
    languageUsed = language.get()

    #get random word
    if languageUsed == "English":
        with open(resource_path("En.json"), "r", encoding="utf-8") as f:
            contents = json.load(f)
        cyphered_word = random.choice(contents[f"{length}"])
    else:
        with open(resource_path("Ru.json"), "r", encoding="utf-8") as f:
            contents = json.load(f)
        cyphered_word = random.choice(contents[f"{length}"])

    #fetch definition in the background
    threading.Thread(target=fetch_definition, daemon=True).start()

    #clear previous grids
    for widget in square_grid.winfo_children():
        widget.destroy()

    for widget in box_grid.winfo_children():
        widget.destroy()
    text_boxes = []

    # Build new grid
    for i in range(attempts):
        row_boxes = []
        for j in range(length):
            txtvar = tk.StringVar()
            txtvar.trace_add("write", lambda *args, v=txtvar: on_change(v))
            text_box = tk.Entry(box_grid, width=2, justify="center",
                            validatecommand=one_letter_cmd, font=font.Font(family="Consolas", size=30, weight="bold"), validate="key", textvariable=txtvar,
                            relief="solid", bg=BACKGROUND_COLOR, fg=TEXT_COLOR,readonlybackground=BACKGROUND_COLOR,
                            highlightbackground="#2a3849",highlightthickness=2, highlightcolor="#2a3849", bd=0)

            text_box.bind("<Control-v>", prevent_paste)
            text_box.bind("<Button-3>", prevent_paste)
            text_box.bind("<Left>", lambda event: event.widget.tk_focusPrev().focus_set(), add="+")
            text_box.bind("<Right>", lambda event: (next_w := event.widget.tk_focusNext(),
                                                    next_w.focus_set(),
                                                    next_w.icursor("end")
                        ))
            text_box.bind("<KeyRelease>", lambda event, row=i, col=j: auto_advance(row=row, col=col, event=event), add="+")
            text_box.bind("<KeyPress>", lambda event, row=i, col=j: auto_backspace(event, row=row, col=col), add="+")
            text_box.bind("<FocusIn>", lambda event, row=i, col=j: on_focus(row, col))
            text_box.bind("<Return>", submit)

            text_box.config(state="readonly")
            text_box.grid(row=i, column=j, padx=2, pady=2)
            row_boxes.append(text_box)
        text_boxes.append(row_boxes)

    #Clear previous keyboard
    for widget in alphabet.winfo_children():
        widget.destroy()

    rows =  ENGLISH if languageUsed == "English" else RUSSIAN
    letter_buttons = {}
    for i in range(len(rows)):
        letter_row_frame = tk.Frame(alphabet, bg=BACKGROUND_COLOR)
        letter_row_frame.pack(anchor="center", pady=2)
        if i == 2:
            enter_button = tk.Button(letter_row_frame, text="Enter", font=font.Font(family="Consolas", size=13, weight="bold"),
                    width=6, foreground=TEXT_COLOR, background="#434d5d", highlightthickness=0, bd=0, pady=12, padx=5,
                    command=submit)
            enter_button.pack(side="left", padx=2)
            
        for letter_pos in rows[i]:
            letter_button = tk.Button(letter_row_frame, text=letter_pos, font=font.Font(family="Consolas", size=13, weight="bold"),
                    width=3, foreground=TEXT_COLOR, background="#434d5d", highlightthickness=0, bd=0, pady=12, padx=5,
                    command=lambda l=letter_pos: button_press(l))
            letter_button.pack(side="left", padx=2)
            letter_buttons[letter_pos] = letter_button
            
        if i == 2:
            tk.Button(letter_row_frame, text="Delete", font=font.Font(family="Consolas", size=13, weight="bold"),
                    width=6, foreground=TEXT_COLOR, background="#434d5d", highlightthickness=0, bd=0, pady=12, padx=5,
                    command=backspace_pressed).pack(side="left", padx=2)
            
    # Reset keyboard colors
    for button in letter_buttons.values():
        button.config(bg="#434d5d")
    
    # Re-enable only the first row
    enable_row(0)
    for r in range(1, attempts):
        disable_row(r)
    
    text_boxes[0][0].focus()
    
    # Hide aftergame frame if it was showing
    aftergame_frame.place_forget()
    aftergame_frame.pack_forget()
    
    # Reset "Enter" button
    enter_button.config(background="#434d5d", text="Enter", command=submit)

    # Unbing Enter from starting game
    root.unbind("<Return>")
    
    # Reset reveal/definition buttons
    custom_word_button.config(text="Reveal Answer")
    definition_button.config(text="Show Definition")

def start_game(event=None):
    global length, attempts
    if length and attempts:
        settings.place_forget()
        play_game()
    else:
        show_popup(message="You must select length and attempts", image=tk.PhotoImage(file=resource_path("x.png")))

def show_popup(message, image=None, duration=2000, TEXT_COLOR=TEXT_COLOR, BACKGROUND_COLOR = BACKGROUND_COLOR):
    # Create a frame on top of everything
    popup = tk.Frame(main, bg=BACKGROUND_COLOR, bd=2, relief="flat")
    popup.place(relx=0.5, rely=0.05, anchor="n")  # top center


    label = tk.Label(popup, image=image, text=message, bg=BACKGROUND_COLOR, fg=TEXT_COLOR, font = font.Font(family="Consolas", size=13, weight="bold"), compound="left")
    label.pack(padx=10, pady=5)
    label.image = image # ALWAYS KEEP REFERENCE
    
    popup.after(duration, popup.destroy)

def assign_color(letters):
    cyphered_letters = list(cyphered_word.upper())
    letter_count = Counter(cyphered_letters)

    for letter_pos in range(len(letters)):
        if letters[letter_pos] == cyphered_letters[letter_pos]: #Correct
            letter_count[letters[letter_pos]] -=1
            color_text_box(current_row,letter_pos,"#279b4e")
            color_button(letters[letter_pos],"#279b4e")

    for letter_pos in range(len(letters)):
        if letters[letter_pos] != cyphered_letters[letter_pos]:
            if letter_count.get(letters[letter_pos],0) >0: #Misplaced
                letter_count[letters[letter_pos]] -=1
                color_text_box(current_row,letter_pos,"#bb9112")
                if letter_buttons[letters[letter_pos]]["bg"] != "#279b4e":
                    color_button(letters[letter_pos],"#bb9112")
            else:       
                color_text_box(current_row,letter_pos,"#434d5d")                    #Incorrect
                if letter_buttons[letters[letter_pos]]["bg"] not in ("#279b4e", "#bb9112"):
                    color_button(letters[letter_pos],"#262828")

def submit(event=None):
    global current_row, status
    letters = [box.get() for box in text_boxes[current_row]]
    word = ("".join(letters)).lower()
    if cyphered_word:
        if (list(cyphered_word.upper())) == letters:
                assign_color(letters)
                for row in range(current_row,attempts):
                    disable_row(row)
                status="Won"
                show_aftergame_frame()

        elif all(len(ch) == 1 and ch.isalpha() for ch in letters):
            if language.get() == "English": 
                with open(resource_path("En_full.txt"), "r", encoding="utf-8") as f:
                    word_list_full = {line.strip() for line in f}
            else:
                with open(resource_path("Ru_full.txt"), "r", encoding="utf-8") as f:
                    word_list_full = {line.strip() for line in f}
            if word in word_list_full or length > 6: 
                assign_color(letters)
                if current_row + 1 >= attempts:
                    disable_row(current_row)
                    status="Lost"
                    show_aftergame_frame()
                    show_popup(image=tk.PhotoImage(file=resource_path("x.png")), message=f"The word was {cyphered_word.upper()}", duration=3600, TEXT_COLOR=TEXT_COLOR)
                else:
                    disable_row(current_row)
                    enable_row(current_row + 1)
                    current_row += 1
            else:
                show_popup(message="There is no such word", image=tk.PhotoImage(file=resource_path("x.png")), duration=1000, TEXT_COLOR=TEXT_COLOR)
        else:
            show_popup(message="Not enough letters", image=tk.PhotoImage(file=resource_path("x.png")), duration=1000, TEXT_COLOR=TEXT_COLOR)

def show_word():
    if custom_word_button["text"] != cyphered_word.upper() :
        custom_word_button.config(text=cyphered_word.upper())
    else:
        custom_word_button.config(text="Reveal Answer")

def show_definition():
    if definition:
        if definition_button["text"] == "Show Definition":
            if definition != None:
                definition_button.config(text=definition, height=definition_button.cget("height")+int(len(definition)/37),wraplength=260)
                aftergame_frame.configure(height=aftergame_frame.cget("height")+14*int(len(definition)/37))
            else:
                definition_button.config(text="No definition")
        else:
            definition_button.config(text="Show Definition", height=1)
            if attempts > 6:
                aftergame_frame.configure(height=500+7*attempts)
            else:
                aftergame_frame.configure(height=500)
    else:
        definition_button.config(text="Loading definition...")


def show_aftergame_frame(event=None):
    if attempts > 6:
        aftergame_frame.configure(height=aftergame_frame.cget("height")+7*attempts)
    root.bind("<Return>", show_settings)
    root.bind("<Button-1>", hide_after_game_on_click)
    root.focus_set
    match status:
        case "Won":
            text = "Won"
            fg = "#279b4e"   
        case "Lost":
            text = "Lost"
            fg = "#a62220"       
    result_label.configure(text=f"YOU {text.upper()}", fg=fg)
    for row in range(len(text_boxes)):
        for col in range(len(text_boxes[row])):
            tk.Label(square_grid, width=4,height=2,border=1, bg=text_boxes[row][col]["readonlybackground"]).grid(row=row,column=col, padx=2,pady=2)  
    aftergame_frame.pack(expand=True, fill="both")
    aftergame_frame.place(relx=0.5, rely=0.5, anchor="center")
    enter_button.config(background="#1844a7",text="Result",command=show_aftergame_frame)

    for row in text_boxes:
        for text_box in row:
            text_box.bind("<Return>", show_aftergame_frame)
    aftergame_frame.lift()

def show_settings(event=None):
    aftergame_frame.place_forget()
    root.bind("<Return>", start_game)
    root.focus_set

    enter_button.config(background="#434d5d",text="Enter",command=lambda: None)

    settings.pack(expand=True, fill="both")
    settings.place(relx=0.5, rely=0.5, anchor="center")
    settings.lift()

### --- UI ---
# Root setup
root = tk.Tk()
root.title("Worldle")
icon = tk.PhotoImage(file=resource_path("ico.png"))
root.iconphoto(True, icon)
root.configure(background="#191a1b")
root.geometry("560x720")
# root.minsize(480,620)
# root.maxsize(480,720)
one_letter_cmd = (root.register(validate_letter), "%P")

# -Main frame-
main = tk.Frame(root,bg = BACKGROUND_COLOR)
main.pack(pady=0, fill="x")

# -Top row components-
header_frame = tk.Frame(main, bg=BACKGROUND_COLOR)
header_frame.pack(fill="x", pady=0)

tk.Label(header_frame, bg=BACKGROUND_COLOR).pack(side="left",padx=25) #spacer

tk.Label(header_frame, 
        text="WORLDLE", 
        font=font.Font(family="Consolas", size=20, weight="bold"),
        bg=BACKGROUND_COLOR, 
        fg=TEXT_COLOR).pack(side="left", expand=True)

settings_image =tk.PhotoImage(file=resource_path("settings.png"))
settings_buton = tk.Button(header_frame, image=settings_image ,highlightthickness=0,bd=0, relief="raised", command=lambda: show_settings() if not settings.winfo_ismapped() else settings.place_forget(), bg=BACKGROUND_COLOR,activebackground=BACKGROUND_COLOR).pack(side="right")
# settings_buton.image = settings_image

# -Settings menu-
settings = tk.Frame(main, bg=POPUP_BACKGROUND_COLOR,width=360, height=500)
settings.pack_propagate(False)
settings_label = tk.Label(settings, bg=POPUP_BACKGROUND_COLOR,text="Settings", fg=TEXT_COLOR, font=font.Font(family="Consolas", size=26, weight="bold"),width=18, height=1)
settings_label.pack(pady=16)

tk.Label(settings, text="Word length:", font=font.Font(family="Consolas", size=14, weight="bold"), bg=POPUP_BACKGROUND_COLOR, fg=TEXT_COLOR).pack()

# Choose length buttons
length_button_frame = tk.Frame(settings, bg=POPUP_BACKGROUND_COLOR)
length_button_frame.pack(anchor="n", pady=3)
length_buttons = []
for i in range(2,9):
    length_button = tk.Button(
        length_button_frame,text=i,font=font.Font(family="Consolas", size=10, weight="bold"),
        width=4,height=2,foreground=TEXT_COLOR,background="#434d5d",highlightthickness=0,bd=0,padx=3,
        command= lambda index=i-2: select_length(index))
    length_buttons.append(length_button)
    length_button.pack(side="left", padx=2)

length_buttons[3].config(bg="#1844a7")

tk.Label(settings,bg=POPUP_BACKGROUND_COLOR,height=1).pack() #Empty spacer

tk.Label(settings, text="Attempts:", font=font.Font(family="Consolas", size=14, weight="bold"), bg=POPUP_BACKGROUND_COLOR, fg=TEXT_COLOR).pack()

# Choose attempts buttons
attempts_button_frame = tk.Frame(settings, bg=POPUP_BACKGROUND_COLOR)
attempts_button_frame.pack(anchor="n", pady=3)
attempt_buttons = []
for i in range(2,9):
    attempt_button = tk.Button(
        attempts_button_frame,text=i,font=font.Font(family="Consolas", size=10, weight="bold"),
        width=4, height=2,foreground=TEXT_COLOR,background="#434d5d",highlightthickness=0,bd=0,padx=3,
        command= lambda index=i-2: select_attempts(index))
    attempt_buttons.append(attempt_button)
    attempt_button.pack(side="left", padx=2)

attempt_buttons[4].config(bg="#1844a7")

tk.Label(settings,bg=POPUP_BACKGROUND_COLOR,height=1).pack() #Empty spacer

tk.Label(settings, text="Language:", font=font.Font(family="Consolas", size=14, weight="bold"), bg=POPUP_BACKGROUND_COLOR, fg=TEXT_COLOR).pack()

#Choose language dropout
root.option_add("*TCombobox*Listbox.background", "#434d5d")
root.option_add("*TCombobox*Listbox.foreground", TEXT_COLOR)
root.option_add("*TCombobox*Listbox.selectBackground", "#434d5d")
root.option_add("*TCombobox*Listbox.selectForeground", TEXT_COLOR)
root.option_add("*TCombobox*Listbox.font", "Consolas 14 bold")
style = ttk.Style()
style.theme_use('clam') 
style.configure("TCombobox", 
        background="#434d5d",
        bordercolor="#434d5d",
        darkcolor="#434d5d",
        lightcolor="#434d5d",
        arrowcolor=TEXT_COLOR)
style.map("TCombobox", 
        background=[("readonly", "#434d5d")],
        fieldbackground=[("readonly", "#434d5d")],
        foreground=[("readonly", TEXT_COLOR)])
language = tk.StringVar()
languageDropOut = ttk.Combobox(settings, textvariable=language, values=["English", "Russian"], style="TCombobox", state="readonly", takefocus=0,width=26,font=font.Font(family="Consolas", size=14, weight="bold"))
language.set("English")
languageDropOut.current(0) 
languageDropOut.bind("<<ComboboxSelected>>", lambda e: languageDropOut.selection_clear())
languageDropOut.bind("<Button-1>", lambda e: languageDropOut.after(1, languageDropOut.selection_clear))

languageDropOut.pack(pady=20)


play_button = tk.Button(settings, command = start_game, text="Play Game",font=font.Font(family="Consolas", size=20, weight="bold"),width=18,
                            bg="#1844a7",fg=TEXT_COLOR,highlightthickness=5,highlightcolor=BACKGROUND_COLOR,bd=0,height=1)
play_button.pack(pady=50,side="bottom")


# -Aftergame frame-
aftergame_frame = tk.Frame(main, bg=POPUP_BACKGROUND_COLOR,width=360, height=500)
aftergame_frame.pack_propagate(False)
result_label = tk.Label(aftergame_frame, bg=POPUP_BACKGROUND_COLOR, font=font.Font(family="Consolas", size=26, weight="bold"),width=18, height=1)  #Win/Lose Title
result_label.pack(pady=7)

tk.Label(aftergame_frame, text="Wordle Attempt",fg=TEXT_COLOR, bg=POPUP_BACKGROUND_COLOR).pack(pady=1) # "Wordle Attempt"

square_grid = tk.Frame(aftergame_frame)                                               # " Grid"
square_grid.configure(background=POPUP_BACKGROUND_COLOR)
square_grid.pack(pady=1)

# tk.Label(aftergame_frame, bg=POPUP_BACKGROUND_COLOR).pack(pady=2)  # empty label to  make more space between buttons and grid 
aftergame_buttons = tk.Frame(aftergame_frame, bg=POPUP_BACKGROUND_COLOR)

custom_word_button = tk.Button(aftergame_buttons, command=show_word, text="Reveal Answer",font=font.Font(family="Consolas", size=10, weight="bold"),width=36,
                                bg="#a62220",fg=TEXT_COLOR,highlightthickness=5,highlightcolor=BACKGROUND_COLOR,bd=0,height=1)
custom_word_button.pack(pady=3)

pixel = tk.PhotoImage(width=1, height=1)
definition_button = tk.Button(aftergame_buttons,command=show_definition, text="Show Definition",font=font.Font(family="Consolas", size=10, weight="bold"),width=36,
                                bg="#bb9112",fg=TEXT_COLOR,highlightthickness=5,highlightcolor=BACKGROUND_COLOR,bd=0,height=1) # make resizable
definition_button.pack(pady=3)

play_again_button = tk.Button(aftergame_buttons, command = show_settings, text="Play again",font=font.Font(family="Consolas", size=10, weight="bold"),width=36,
                                bg="#1844a7",fg=TEXT_COLOR,highlightthickness=5,highlightcolor=BACKGROUND_COLOR,bd=0,height=1)
play_again_button.pack(pady=3)

aftergame_buttons.pack(side="bottom", pady=20)


# -Visual Grid-
box_grid = tk.Frame(main)
box_grid.configure(background=BACKGROUND_COLOR)
box_grid.pack(pady=20)

text_boxes = []
for i in range(6):
    rows = []
    for j in range(5):
        text_box = tk.Entry(box_grid, width=2, justify="center",
                            font=font.Font(family="Consolas", size=30, weight="bold"),
                            relief="solid", bg=BACKGROUND_COLOR, fg=TEXT_COLOR,readonlybackground=BACKGROUND_COLOR,
                            highlightbackground="#2a3849",highlightthickness=2, highlightcolor="#2a3849", bd=0, state="readonly")
        text_box.grid(row=i,column=j, padx=2,pady=2)
        rows.append(text_box)
    text_boxes.append(rows)

# -Keyboard-
alphabet = tk.Frame(main)
alphabet.configure(background=BACKGROUND_COLOR)
alphabet.pack()

rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
letter_buttons = {}
for i in range(len(rows)):
    letter_row_frame = tk.Frame(alphabet, bg=BACKGROUND_COLOR)
    letter_row_frame.pack(anchor="center", pady=2)
    if i == 2:
        enter_button = tk.Button(letter_row_frame, text="Enter", font=font.Font(family="Consolas", size=13, weight="bold"),
                width=6, foreground=TEXT_COLOR, background="#434d5d", highlightthickness=0, bd=0, pady=12, padx=5,
                command=submit)
        enter_button.pack(side="left", padx=2)
        
    for letter_pos in rows[i]:
        letter_button = tk.Button(letter_row_frame, text=letter_pos, font=font.Font(family="Consolas", size=13, weight="bold"),
                width=3, foreground=TEXT_COLOR, background="#434d5d", highlightthickness=0, bd=0, pady=12, padx=5,
                command=lambda l=letter_pos: button_press(l))
        letter_button.pack(side="left", padx=2)
        letter_buttons[letter_pos] = letter_button
        
    if i == 2:
        tk.Button(letter_row_frame, text="Delete", font=font.Font(family="Consolas", size=13, weight="bold"),
                width=6, foreground=TEXT_COLOR, background="#434d5d", highlightthickness=0, bd=0, pady=12, padx=5,
                command=backspace_pressed).pack(side="left", padx=2)

show_settings()
root.mainloop()