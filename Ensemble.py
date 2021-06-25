from multiprocessing import Process, Pipe
import socket
from sys import byteorder
from Ringers import ringers
from Methods import methods, Method
from Strike import ring_bells
from Config import Config
from PIL import Image
from threading import Thread
from tkinter import *
from tkinter import ttk
import traceback

class PlayableExtent():
    def __init__(self, method, extent_key):
        self.method = method
        self.extent_key = extent_key
    
    def __str__(self):
        return self.method.name + ' - ' + self.method.extent_name(self.extent_key)
    
    def name(self):
        return self.method.extent_name(self.extent_key)
    
    def coverable(self):
        return self.method.coverable()
    
    def number_of_bells(self):
        return self.method.number_of_bells()
    
    def method_name(self):
        return self.method.name
    
    def extent_id(self):
        return self.extent_key
    
    def selected(self, event):
        global selected_method, started, add_cover
        
        selected_method = self
        
        started = stop()
        # If a Minor, Major, etc then no cover
        if selected_method.coverable():
            add_cover_checkbox['state'] = 'normal'
            add_cover.set(True)
        else:
            add_cover_checkbox['state'] = 'disabled'
            add_cover.set(False)
        courses.set(1)
        intros.set(1)
        parent_ringer.send("ResetAll")
        manage_bell_selection(selected_method.number_of_bells(), add_cover)
        set_to_handstroke(bell_ropes)
        progress.set(0)

def playable_extents(mcf_list):
    methods = []
    for mcf in mcf_list:
        methods.append(Method('./data/' + mcf[1] + '.mcf'))
    playable = []
    for m in methods:
        extent_id = 1
        while m.extent_exists(extent_id):
            playable.append(PlayableExtent(m, 'EXTENT-' + str(extent_id)))
            extent_id += 1

    return playable

def methods_treeview(parent, mcf_list):
    tree = ttk.Treeview(parent, height = 5, show = 'tree')
    for mcf in mcf_list:
        method = Method('./data/' + mcf[1] + '.mcf')
        branch = tree.insert('', 'end', mcf[1], text = method.name, values = (method,))
        extent_id = 1
        while method.extent_exists(extent_id):
            extent = PlayableExtent(method, 'EXTENT-' + str(extent_id))
            tree.insert(branch, 'end', extent, text = extent.name(), tags = (extent,))
            tree.tag_bind(extent, '<<TreeviewSelect>>', extent.selected)
            extent_id += 1
    
    return tree

def manage_bell_selection(number_of_bells, add_cover):
    for ndx in range(len(bell_selector_checkboxes)):
        bell_selector_vars[ndx].set(False)
        bell_selector_checkboxes[ndx]['state'] = 'normal'
        bell_selector_checkboxes[ndx]['text'] = str(ndx + 1) + '     '
        bell_controller(ndx + 1, bell_selector_vars[ndx])
    bell_selector_checkboxes[0]['text'] = 'Treble'
    nob = number_of_bells
    if nob % 2 != 0 and add_cover.get() and nob < MAX_BELLS:
        nob += 1
    bell_selector_checkboxes[nob - 1]['text'] = 'Tenor '
    for ndx in range(nob, len(bell_selector_checkboxes)):
        bell_selector_checkboxes[ndx]['state'] = 'disabled'

def start():
    parent_method.send("Start")
    parent_ringer.send("Start")
    
    return True

def stop():
    parent_method.send("Stop")
    parent_ringer.send("Stop")
    
    return False

def bell_controller(bell_id, selected):
    parent_method.send("Play," + str(bell_id) + "," + ("False" if selected.get() else "True"))
    parent_ringer.send("ListenFor," + str(bell_id) + "," + ("True" if selected.get() else "False"))

def bell_indicators():
    INDICATE_BELL_HANDSTROKE = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_bell') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_shift')
    INDICATE_BELL_BACKSTROKE = INDICATE_BELL_HANDSTROKE + \
                               (config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_stroke_mask') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_stroke_shift'))
    INDICATE_BELL_GRAPHIC_CLEAR = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_graphic') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_shift')
    INDICATE_BELL_GRAPHIC_SHOW = INDICATE_BELL_GRAPHIC_CLEAR + \
                                 (config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_graphic_mask') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_graphic_shift'))
    INDICATE_BELL_NUMBER_SHIFT = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_bell_number_shift')
    hand = {}
    back = {}
    graphic_show = {}
    graphic_clear = {}
    for ndx in range(config.getint('BELLS', 'bells')):
        hand[INDICATE_BELL_HANDSTROKE | (ndx << INDICATE_BELL_NUMBER_SHIFT)] = ndx
        back[INDICATE_BELL_BACKSTROKE | (ndx << INDICATE_BELL_NUMBER_SHIFT)] = ndx
        graphic_show[INDICATE_BELL_GRAPHIC_SHOW | (ndx << INDICATE_BELL_NUMBER_SHIFT)] = ndx
        graphic_clear[INDICATE_BELL_GRAPHIC_CLEAR | (ndx << INDICATE_BELL_NUMBER_SHIFT)] = ndx
    
    return hand, back, graphic_show, graphic_clear

def set_to_handstroke(ropes):
    for ndx in range(MAX_BELLS):
        ropes[ndx]['image'] = sally_pic
    
def gui_events_listener(addr, port, window):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((addr, port))
    EXIT = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_exit')
    handstroke_indicators, backstroke_indicators, graphic_show_indicators, graphic_clear_indicators = bell_indicators()

    while True:
        data, from_addr = sock.recvfrom(8)
        command = int.from_bytes(data, byteorder)
        if command in handstroke_indicators:
            window.event_generate('<<BELL_HAND_STROKE_' + str(handstroke_indicators[command]) + '>>')
        elif command in backstroke_indicators:
            window.event_generate('<<BELL_BACK_STROKE_' + str(backstroke_indicators[command]) + '>>')
        elif command in graphic_show_indicators:
            window.event_generate('<<INDICATE_SHOW_' + str(graphic_show_indicators[command]) + '>>')
        elif command in graphic_clear_indicators:
            window.event_generate('<<INDICATE_CLEAR_' + str(graphic_clear_indicators[command]) + '>>')
        elif command == EXIT:
            break

def pace_change(value):
    parent_method.send("Pace," + str(value))

def courses_change():
    started = stop()

def intros_change():
    started = stop()

def add_cover_change():
    started = stop()
    if selected_method:
        manage_bell_selection(selected_method.number_of_bells(), add_cover)
    set_to_handstroke(bell_ropes)

def gui_look_to():
    global started
    
    started = stop()
    set_to_handstroke(bell_ropes)
    progress_bar['maximum'] = selected_method.method.extent_size(selected_method.extent_id(), add_cover.get(), intros.get(), courses.get())
    progress.set(0)
    request = "Load," + selected_method.method_name() + "," + selected_method.extent_id() + ","
    if not add_cover.get():
        request = request + "no"
    request = request + "cover," + str(intros.get()) + ',' + str(courses.get()) + ',' + str(wait_learner.get())
    parent_method.send(request)
    started = start()

def gui_stand():
    started = stop()
    set_to_handstroke(bell_ropes)
    
def gui_exit():
    sock.sendto(config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_exit').to_bytes(1, byteorder), (config.get('GUI_EVENT_LISTENER', 'addr',), config.getint('GUI_EVENT_LISTENER', 'port')))
    window.destroy()

def bell_selected_callback(bell_id, selected):
    s = selected
    s.set(False)
    b = bell_id + 1
    return lambda : bell_controller(b, s)

def handstroke_callback(bell_id):
    b = bell_id
    return lambda event : show_handstroke(b)

def show_handstroke(bell_id):
    if started and animated_ropes.get():
        progress.set(progress.get() + 1)
        bell_ropes[bell_id]['image'] = sally_pic
            
def backstroke_callback(bell_id):
    b = bell_id
    return lambda event : show_backstroke(b)

def show_backstroke(bell_id):
    if started and animated_ropes.get():
        progress.set(progress.get() + 1)
        bell_ropes[bell_id]['image'] = tail_pic
            
def indicate_show_callback(bell_id):
    b = bell_id
    return lambda event : show_indicator(b)

def show_indicator(bell_id):
    if started and bong_along.get():
        bell_pull_indicators[bell_id]['image'] = indicator_bell_pic
            
def indicate_clear_callback(bell_id):
    b = bell_id
    return lambda event : clear_indicator(b)

def clear_indicator(bell_id):
    if started and bong_along.get():
        bell_pull_indicators[bell_id]['image'] = indicator_blank_pic

def center(window):
    window.update_idletasks()
    width = window.winfo_width()
    frm_width = window.winfo_rootx() - window.winfo_x()
    win_width = width + 2 * frm_width
    height = window.winfo_height()
    titlebar_height = window.winfo_rooty() - window.winfo_y()
    win_height = height + titlebar_height + frm_width # seems strange to use width in height calculation
    x = window.winfo_screenwidth() // 2 - win_width // 2
    y = window.winfo_screenheight() // 2 - win_height // 2
    window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    window.deiconify()
            
if __name__ == '__main__':
    config = Config('ensemble.ini')
    
    MAX_BELLS = config.getint('BELLS', 'bells')
    
    parent_method, child_method = Pipe()
    parent_ringer, child_ringer = Pipe()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    ringer = Process(target = ringers, args = (child_ringer, parent_method, config.get('STRIKE', 'addr'), config.getint('STRIKE', 'port')))
    ringer.start()
    method = Process(target = methods, args = (child_method, config.get('STRIKE', 'addr'), config.getint('STRIKE', 'port')))
    method.start()
    bells = Process(target = ring_bells, args = (config.get('STRIKE', 'addr'), config.getint('STRIKE', 'port')))
    bells.start()
    
    started = False
    
    window = Tk()
    
    style = ttk.Style()
    style.theme_use('alt')
    
    window.title('Ringable Ensemble')
    window.columnconfigure(0, weight = 1)
    window.rowconfigure(0, weight = 1)
    window.protocol("WM_DELETE_WINDOW", gui_exit)
    
    add_cover = BooleanVar(window)
    add_cover.set(True)
    bong_along = BooleanVar(window)
    bong_along.set(True)
    wait_learner = BooleanVar(window)
    wait_learner.set(False)
    animated_ropes = BooleanVar(window)
    animated_ropes.set(True)
    courses = IntVar(window)
    courses.set(1)
    intros = IntVar(window)
    intros.set(1)
    
    main_frame = ttk.Frame(window, relief = 'raised', borderwidth = 2)
    main_frame.grid(column = 0, row = 0, sticky = NSEW)
    main_frame.columnconfigure(0, weight = 1)
    for ndx in range(5):
        main_frame.rowconfigure(ndx, weight = 1)
    
    method_frame = ttk.LabelFrame(main_frame, text = 'Select Method')
    method_frame.grid(column = 0, row = 0, padx = 10, pady = 10, sticky = NSEW)
    method_frame.columnconfigure(0, weight = 1)
    method_frame.rowconfigure(0, weight = 1)
    methods = methods_treeview(method_frame, config.items('MCF'))
    methods.grid(column = 0, row = 1, sticky = NSEW)
    methods_scroll_bar = ttk.Scrollbar(method_frame, orient = 'vertical', command = methods.yview)
#    methods_scroll_bar = Scrollbar(method_frame, orient = 'vertical', command = methods.yview)
    methods_scroll_bar.grid(column = 1, row = 1, sticky = (N, S, W))
    methods['yscrollcommand'] = methods_scroll_bar.set

    checkboxes_frame = ttk.Frame(main_frame)
    checkboxes_frame.grid(column = 0, row = 1, padx = 10, pady = 10, sticky = NSEW)
    for col in range(4):
        checkboxes_frame.columnconfigure(col, weight = 1)
    checkboxes_frame.rowconfigure(0, weight = 1)
    add_cover_checkbox = ttk.Checkbutton(checkboxes_frame, text = 'Add cover bell', variable = add_cover, command = add_cover_change)
    add_cover_checkbox.grid(column = 0, row = 0, padx = 3, pady = 3)
    bong_along_checkbox = ttk.Checkbutton(checkboxes_frame, text = 'Bong-along', variable = bong_along)
    bong_along_checkbox.grid(column = 1, row = 0, padx = 3, pady = 3)
    wait_learner_checkbox = ttk.Checkbutton(checkboxes_frame, text = 'Wait for ringer', variable = wait_learner)
    wait_learner_checkbox.grid(column = 2, row = 0, padx = 3, pady = 3)
    animated_ropes_checkbox = ttk.Checkbutton(checkboxes_frame, text = 'Animated ropes', variable = animated_ropes)
    animated_ropes_checkbox.grid(column = 3, row = 0, padx = 3, pady = 3)
    
    method_control_frame = ttk.Frame(main_frame)#, borderwidth = 5, relief = RAISED)
    method_control_frame.grid(column = 0, row = 2, padx = 10, pady = 10, sticky = NSEW)
    for col in range(3):
        method_control_frame.columnconfigure(col, weight = 1)
    method_control_frame.rowconfigure(0, weight = 1)
    pace_frame = ttk.Frame(method_control_frame)#, borderwidth = 5, relief = RAISED)
    pace_frame.grid(column = 0, row = 0, padx = 3)#, sticky = EW)
    ttk.Label(pace_frame, text = 'Set pace of rounds').grid(column = 0, row = 0, padx = 3, pady = 3)
    pace_scale = Scale(pace_frame, from_ = 2.0, to = 5.0, orient = HORIZONTAL, resolution = 0.1, length = 200, tickinterval = 1.0, command = pace_change)
    pace_scale.set(3.0)
    pace_scale.grid(column = 1, row = 0, padx = 3, pady = 3)
    
    courses_frame = ttk.Frame(method_control_frame)#, borderwidth = 5, relief = RAISED)
    courses_frame.grid(column = 1, row = 0, padx = 3)#, sticky = EW)
    ttk.Label(courses_frame, text = 'Courses').grid(column = 2, row = 0, padx = 3, pady = 3)
    courses_spin = Spinbox(courses_frame, from_ = 1, to = 4, command = courses_change, state = 'readonly', textvariable = courses, width = 2, justify = CENTER)
    courses_spin.grid(column = 3, row = 0, padx = 3, pady = 3)
    
    intros_frame = ttk.Frame(method_control_frame)#, borderwidth = 5, relief = RAISED)
    intros_frame.grid(column = 2, row = 0, padx = 3)#, sticky = EW)
    ttk.Label(intros_frame, text = 'Intro rounds').grid(column = 4, row = 0, padx = 3, pady = 3)
    intros_spin = Spinbox(intros_frame, from_ = 1, to = 4, command = intros_change, state = 'readonly', textvariable = intros, width = 2, justify = CENTER)
    intros_spin.grid(column = 5, row = 0, padx = 3, pady = 3)
    
    bell_rope_frame = ttk.LabelFrame(main_frame, text = 'Select Bells to be controlled by buttons')
    bell_rope_frame.grid(column = 0, row = 3, padx = 10, pady = 10, sticky = NSEW)
    bell_rope_frame.rowconfigure(0, weight = 1)
    bell_pull_indicators = []
    bell_ropes = []
    bell_selector_vars = []
    bell_selector_checkboxes = []
    indicator_blank_pic = PhotoImage(file = './data/IndicatorBlank.png')
    indicator_bell_pic = PhotoImage(file = './data/IndicatorBell.png')
    sally_pic = PhotoImage(file = './data/SmallSally.png')
    tail_pic = PhotoImage(file = './data/SmallTail.png')
    for ndx in range(MAX_BELLS):
        bell_rope_frame.columnconfigure(ndx, weight = 1)
        indicator = Label(bell_rope_frame, image = indicator_blank_pic, width = indicator_blank_pic.width(), height = indicator_blank_pic.height())
        indicator.grid(column = ndx, row = 0, padx = 3, pady = 3, sticky = EW)
        bell_pull_indicators.append(indicator)
        window.bind('<<INDICATE_SHOW_' + str(ndx) + '>>', func = indicate_show_callback(ndx))
        window.bind('<<INDICATE_CLEAR_' + str(ndx) + '>>', func = indicate_clear_callback(ndx))
        
        rope = Label(bell_rope_frame, image = sally_pic, width = sally_pic.width(), height = sally_pic.height())
        rope.grid(column = ndx, row = 1, padx = 50, pady = 3, sticky = EW)
        bell_ropes.append(rope)
        window.bind('<<BELL_HAND_STROKE_' + str(ndx) + '>>', func = handstroke_callback(ndx))
        window.bind('<<BELL_BACK_STROKE_' + str(ndx) + '>>', func = backstroke_callback(ndx))
        
        bell_selector_vars.append(BooleanVar(bell_rope_frame))
        check = ttk.Checkbutton(bell_rope_frame, text = str(ndx + 1) + '     ', variable = bell_selector_vars[ndx], command = bell_selected_callback(ndx, bell_selector_vars[ndx]))
        check.grid(column = ndx, row = 2, padx = 3, pady = 3)#, sticky = EW)
        bell_selector_checkboxes.append(check)
    
    progress_frame = ttk.Frame(main_frame)
    progress_frame.grid(column = 0, row = 4, padx = 10, pady = 10, sticky = NSEW)
    progress_frame.columnconfigure(0, weight = 1)
    progress_frame.rowconfigure(0, weight = 1)
    progress = IntVar(window)
    progress_bar = ttk.Progressbar(progress_frame, length = 100, mode = 'determinate', orient = HORIZONTAL, variable = progress)
    progress_bar.grid(column = 0, row = 0, padx = 10, pady = 10, sticky = EW)
    
    button_frame = ttk.Frame(main_frame, relief = RAISED, borderwidth = 2)
    button_frame.grid(column = 0, row = 5, padx = 10, pady = 10,  sticky = NSEW)
    button_frame.columnconfigure(0, weight = 0)
    button_frame.columnconfigure(1, weight = 1)
    button_frame.columnconfigure(2, weight = 0)
    button_frame.rowconfigure(0, weight = 1)
    look_to_button = ttk.Button(button_frame, text = 'Look To', command = gui_look_to)
    look_to_button.grid(column = 0, row = 0, padx = 3, pady = 3, sticky = W)
    stand_button = ttk.Button(button_frame, text = 'Stand', command = gui_stand)
    stand_button.grid(column = 1, row = 0, padx = 3, pady = 3, sticky = W)
    exit_button = ttk.Button(button_frame, text = 'Exit', command = gui_exit)
    exit_button.grid(column = 2, row = 0, padx = 3, pady = 3, sticky = E)
    
    gui_events = Thread(target = gui_events_listener, args = (config.get('GUI_EVENT_LISTENER', 'addr'), config.getint('GUI_EVENT_LISTENER', 'port'), window))
    gui_events.start()
    
    center(window)
    
    window.mainloop()

    gui_events.join()
    
    parent_method.send("Exit")
    method.join()
    
    parent_ringer.send("Exit")
    ringer.join()
    
    sock.sendto(config.getint('STRIKE_COMMANDS', 'exit').to_bytes(1, byteorder), (config.get('STRIKE', 'addr'), config.getint('STRIKE', 'port')))
    bells.join()
