from threading import Thread
import socket
from time import sleep
from sys import byteorder
from Config import Config
import configparser
from Row import Row
import os
import sys
from random import randrange

def bell_indicators(MAX_BELLS,
                    INDICATE_BELL_NUMBER_SHIFT,
                    INDICATE_BELL_HANDSTROKE,
                    INDICATE_BELL_BACKSTROKE,
                    INDICATE_BELL_GRAPHIC_SHOW,
                    INDICATE_BELL_GRAPHIC_CLEAR):
    hand = {}
    back = {}
    graphic_show = {}
    graphic_clear = {}
    for ndx in range(MAX_BELLS):
        hand[ndx] = INDICATE_BELL_HANDSTROKE | (ndx << INDICATE_BELL_NUMBER_SHIFT)
        back[ndx] = INDICATE_BELL_BACKSTROKE | (ndx << INDICATE_BELL_NUMBER_SHIFT)
        graphic_show[ndx] = INDICATE_BELL_GRAPHIC_SHOW | (ndx << INDICATE_BELL_NUMBER_SHIFT)
        graphic_clear[ndx] = INDICATE_BELL_GRAPHIC_CLEAR | (ndx << INDICATE_BELL_NUMBER_SHIFT)
    
    return hand, back, graphic_show, graphic_clear

class Row():
  def __init__(self, number_of_bells):
    self.positions = [None for ndx in range(number_of_bells)]
    self.call_go = False
    self.call_thats_all = False
    self.call_bob = False
    self.call_single = False
    self.call_stand = False
  
  def __str__(self):
    say = ''
    if self.call_go:
      say += 'Go Method '
    if self.call_thats_all:
      say += 'Thats All '
    if self.call_bob:
      say += 'Bob '
    if self.call_single:
      say += 'Single '
    if self.call_stand:
      say += 'Stand Next '
    
    say += str(self.positions)
    
    return say

class Extent():
  LEAD_TYPE_PLAIN = 'P'
  LEAD_TYPE_BOB = 'B'
  LEAD_TYPE_SINGLE = 'S'
  
  def __init__(self, method, extent_id, cover = True, intro_courses = 1, extent_courses = 1, wait_learner = False):
    self.name = method.extent_name(extent_id)
    self.length = method.extent_length(extent_id) * extent_courses
    self.definition = method.extent_definition(extent_id)
    self.wait = wait_learner
    # If the extent is mutable it can be shift shuffled
    # The sections that can be shifted are delimited by '-' characters so will be split, shifted and then stuck togather
    if method.extent_mutable(extent_id):
        # Remove all formatting spaces
        self.definition = self.definition.replace(' ', '')
        # Break into sections
        sections = self.definition.split('-')
        for ndx in range(len(sections)):
            s = sections[ndx]
            # Decide how many shifts to perform on the section
            shifts = randrange(len(s))
            for shift in range(shifts):
                s = s[-1] + s[0:-1]
            sections[ndx] = s
        # Reassemble the sections
        self.definition = ''.join(sections)
    # The number of bells being rung is the number of bells in the method plus the optional cover
    self.number_of_bells = method.number_of_bells()
    self.cover = cover
    if self.cover:
      self.number_of_bells += 1
    
    # A reference to the parent method is only needed for dumping to text
    self.method = method
    
    self.rows = []

    # The last lead is 'plain' to force a plain start in the first lead
    last_lead = Extent.LEAD_TYPE_PLAIN
    for courses in range(extent_courses):
      # Build the course
      for lead in self.definition:
        Extent._add_lead_start(last_lead, self.rows, method, self.length, cover)
        if lead in ('p', 'P'):
          Extent._add_plain(self.rows, method, self.length, cover)
          last_lead = Extent.LEAD_TYPE_PLAIN
        elif lead in ('b', 'B'):
          Extent._add_bob(self.rows, method, self.length, cover)
          last_lead = Extent.LEAD_TYPE_BOB
        elif lead in ('s', 'S'):
          Extent._add_single(self.rows, method, self.length, cover)
          last_lead = Extent.LEAD_TYPE_SINGLE
    
    # Add the intro rounds and the Go Method call to the last backstroke of the intro
    intro = []
    for ndx in range(intro_courses):
      Extent._add_round(intro, self.number_of_bells)
    intro[((intro_courses - 1) * 2) + 1].call_go = True
    self.rows = intro + self.rows
    
    # Add That's All to the second to last row of the extent
    self.rows[len(self.rows) - 2].call_thats_all = True
        
    # If the extent ended on a back stroke add the extra half round
    if len(self.rows) % 2 != 0:
      Extent._add_half_round(self.rows, self.number_of_bells)
    
    # Add the final rounds and the call to Stand
    Extent._add_round(self.rows, self.number_of_bells)
    self.rows[len(self.rows) - 2].call_stand = True
    
  def _add_half_round(rows, bells):
    row = Row(bells)
    for ndx in range(bells):
      row.positions[ndx] = ndx + 1
    rows.append(row)

  def _add_round(rows, bells):
    Extent._add_half_round(rows, bells)
    Extent._add_half_round(rows, bells)

  def _add_lead_start(last_lead, rows, method, length, cover):
    if last_lead == Extent.LEAD_TYPE_PLAIN:
      Extent._apply(rows, method.number_of_bells(), method.plain_start, length, cover)
    elif last_lead == Extent.LEAD_TYPE_BOB:
      Extent._apply(rows, method.number_of_bells(), method.bob_start, length, cover)
    elif last_lead == Extent.LEAD_TYPE_SINGLE:
      Extent._apply(rows, method.number_of_bells(), method.single_start, length, cover)

  def _add_plain(rows, method, length, cover):
    Extent._apply(rows, method.number_of_bells(), method.tracks, length, cover)
    Extent._apply(rows, method.number_of_bells(), method.plain, length, cover)

  def _add_bob(rows, method, length, cover):
    Extent._apply(rows, method.number_of_bells(), method.tracks, length, cover)
    # Call the Bob at the beginning of the last row BEFORE the Bob
    rows[len(rows) - 1].call_bob = True
    Extent._apply(rows, method.number_of_bells(), method.bob, length, cover)

  def _add_single(rows, method, length, cover):
    Extent._apply(rows, method.number_of_bells(), method.tracks, length, cover)
    # Call the Single at the beginning of the last row BEFORE the Single
    rows[len(rows) - 1].call_single = True
    Extent._apply(rows, method.number_of_bells(), method.single, length, cover)

  def _apply(rows, number_of_bells, work, length, cover):
    prev = len(rows) - 1
    bells = number_of_bells
    if cover:
      bells += 1
    
    if len(work) > 0:
      for ndx in range(len(work[0])):
          if length > len(rows):
              row = Row(bells)
              if cover:
                row.positions[bells -1] = bells
              rows.append(row)

      for track in range(number_of_bells):
          if prev < 0:
              bell = track + 1
          else:
              bell = rows[prev].positions[track]
          curr = prev + 1
          for t in work[track]:
              if curr < length:
                  rows[curr].positions[t - 1] = bell
                  curr += 1
  
  def to_mdf(self):
    print('[INFO]')
    print('name={} {}'.format(self.method.name, self.name))
    print('bells={}'.format(self.method.number_of_bells()))
    print('rows={}'.format(self.length))
    print()
    # For dump purposes 'assume' there are two intro and two extro rounds
    print('[ROWS]')
    row_id = 1
    for ndx in range(self.length):
      r = self.rows[ndx + 2]
      print('M{:04}='.format(row_id,), end = '')
      if r.call_bob:
        print('(B) ', end = '')
      if r.call_single:
        print('(S) ', end = '')
      for p in range(self.method.number_of_bells()):
        print('{} '.format(r.positions[p]), end = '')
      print()
      row_id += 1

  def dump(self):
    row_id = -1
    for r in self.rows:
      print('M{:04}='.format(row_id,), end = '')
      if r.call_bob:
        print('(B) ', end = '')
      if r.call_single:
        print('(S) ', end = '')
      for p in r.positions:
        print('{} '.format(p), end = '')
      print()
      row_id += 1

class Method():
  def __init__(self, file):
    self.definition = configparser.ConfigParser()
    self.definition.optionxform = str # Don't want keys to be lower cased
    
    self.definition.read(file)
    self.name = self.definition.get('INFO', 'name')

    self.tracks = {}
    for key in self.definition['TRACKS']:
      self.tracks[int(key) - 1] = [int(v) for v in self.definition['TRACKS'][key].split()]

    # Just in case a method is added where the Bobs and singles have an
    # effect across the end of a lead and into the start of the next lead. To account for
    # this the concept of the start of a lead being different depending on the previous
    # lead was introduced. The PLAIN_START, BOB_START and SINGLE_START sections of the
    # definition files are optional as they are not necessary for most mothods
    self.plain_start = {}
    if self.definition.has_section('PLAIN_START'):
      for key in self.definition['PLAIN_START']:
        self.plain_start[int(key) - 1] = [int(v) for v in self.definition['PLAIN_START'][key].split()]
      
    self.plain = {}
    if self.definition.has_section('PLAIN'):
      for key in self.definition['PLAIN']:
        self.plain[int(key) - 1] = [int(v) for v in self.definition['PLAIN'][key].split()]

    self.bob_start = {}
    if self.definition.has_section('BOB_START'):
      for key in self.definition['BOB_START']:
        self.bob_start[int(key) - 1] = [int(v) for v in self.definition['BOB_START'][key].split()]
      
    self.bob = {}
    if self.definition.has_section('BOB'):
      for key in self.definition['BOB']:
        self.bob[int(key) - 1] = [int(v) for v in self.definition['BOB'][key].split()]

    self.single_start = {}
    if self.definition.has_section('SINGLE_START'):
      for key in self.definition['SINGLE_START']:
        self.single_start[int(key) - 1] = [int(v) for v in self.definition['SINGLE_START'][key].split()]
      
    self.single = {}
    if self.definition.has_section('SINGLE'):
      for key in self.definition['SINGLE']:
        self.single[int(key) - 1] = [int(v) for v in self.definition['SINGLE'][key].split()]
  
  def name(self):
    return self.name
  
  def extent_exists(self, extent_id):
    key = 'EXTENT-' + str(extent_id)
    return key in self.definition
    
  def number_of_bells(self):
    return self.definition.getint('INFO', 'bells')
    
  def coverable(self):
    return self.definition.getboolean('INFO', 'coverable', fallback = False)
    
  def extent_name(self, key):
    return self.definition.get(key, 'NAME')
  
  def extent_length(self, key):
    return self.definition.getint(key, 'LENGTH')

  def extent_size(self, key, cover, intros, courses):
      bells = self.number_of_bells()
      if self.coverable() and cover:
          bells += 1
          
      size = self.extent_length(key) * bells * courses
      size += intros * bells * 2
      size += bells * 2 # Always two extro rounds
      
      return size
  
  def extent_definition(self, key):
    return self.definition.get(key, 'DEFINITION')

  def extent_mutable(self, key):
    return self.definition.getboolean(key, 'MUTABLE', fallback = False)
    
def methods(conn, ring_addr, ring_port):
    app_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))

    config = Config()

    MAX_BELLS = config.getint('BELLS', 'bells')
    GO = config.getint('STRIKE_COMMANDS', 'go')
    THATS_ALL = config.getint('STRIKE_COMMANDS', 'thats_all')
    BOB = config.getint('STRIKE_COMMANDS', 'bob')
    SINGLE = config.getint('STRIKE_COMMANDS', 'single')
    STAND = config.getint('STRIKE_COMMANDS', 'stand_next')
    INDICATE_BELL_NUMBER_SHIFT = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_bell_number_shift')
    INDICATE_BELL_HANDSTROKE = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_bell') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_shift')
    INDICATE_BELL_BACKSTROKE = INDICATE_BELL_HANDSTROKE + \
                               (config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_stroke_mask') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_stroke_shift'))
    INDICATE_BELL_GRAPHIC_CLEAR = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_graphic') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_shift')
    INDICATE_BELL_GRAPHIC_SHOW = INDICATE_BELL_GRAPHIC_CLEAR + \
                                 (config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_graphic_mask') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_graphic_shift'))
                                 
    handstroke_indicators, backstroke_indicators, graphic_show_indicators, graphic_clear_indicators = bell_indicators(MAX_BELLS,
                                                                                                                      INDICATE_BELL_NUMBER_SHIFT,
                                                                                                                      INDICATE_BELL_HANDSTROKE,
                                                                                                                      INDICATE_BELL_BACKSTROKE,
                                                                                                                      INDICATE_BELL_GRAPHIC_SHOW,
                                                                                                                      INDICATE_BELL_GRAPHIC_CLEAR)
    
    bells = [True] * MAX_BELLS
    bells_rung = [False] * MAX_BELLS
    stop_playing = False
    method = None
    extent = None
    pace = 3.0
    pause = pace / MAX_BELLS
    courses = 1
    intro_rounds = 1
    
    def play(ring_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ndx = 0
        stroke_type = "B"
        LOOK_TO = config.getint('STRIKE_COMMANDS', 'look_to')
        
        sock.sendto(LOOK_TO.to_bytes(1, byteorder), (ring_addr, ring_port))
        sleep(4)
        
        for row in extent.rows:
          if stop_playing:
            break
          if row.call_go:
            sock.sendto(GO.to_bytes(1, byteorder), (ring_addr, ring_port))
          if row.call_thats_all:
            sock.sendto(THATS_ALL.to_bytes(1, byteorder), (ring_addr, ring_port))
          if row.call_bob:
            sock.sendto(BOB.to_bytes(1, byteorder), (ring_addr, ring_port))
          if row.call_single:
            sock.sendto(SINGLE.to_bytes(1, byteorder), (ring_addr, ring_port))
          if row.call_stand:
            sock.sendto(STAND.to_bytes(1, byteorder), (ring_addr, ring_port))
          stroke_type = "H" if stroke_type == "B" else "B"
          for strike in row.positions:
            if stop_playing:
              break
            sock.sendto(graphic_show_indicators[strike - 1].to_bytes(1, byteorder), (config.get('GUI_EVENT_LISTENER', 'addr',), config.getint('GUI_EVENT_LISTENER', 'port')))
            sleep(pause / 2.0)
            if stroke_type == 'H':
                indicator = backstroke_indicators[strike - 1]
            else:
                indicator = handstroke_indicators[strike - 1]
            sock.sendto(indicator.to_bytes(1, byteorder), (config.get('GUI_EVENT_LISTENER', 'addr',), config.getint('GUI_EVENT_LISTENER', 'port')))
            if bells[strike - 1]:
              sock.sendto(strike.to_bytes(1, byteorder), (ring_addr, ring_port))
            else:
                if extent.wait:
                    while not bells_rung[strike - 1] and not stop_playing:
                        sleep(0.01)
                    bells_rung[strike - 1] = False
            sleep(pause / 2.0)
            sock.sendto(graphic_clear_indicators[strike - 1].to_bytes(1, byteorder), (config.get('GUI_EVENT_LISTENER', 'addr',), config.getint('GUI_EVENT_LISTENER', 'port')))
          if stroke_type == 'B':
            # Hand stroke lead pause
            sleep(pause)
            
    t = None
    while True:
        command = conn.recv().split(",")
        if command[0] == "Exit":
            stop_playing = True
            if t and t.is_alive():
                t.join()
            break
        elif command[0] == "Start":
            stop_playing = False
            if method:
                t = Thread(target = play, args = (ring_port,))
                t.start()
        elif command[0] == "Stop":
            stop_playing = True
            if t and t.is_alive():
                t.join()
        elif command[0] == 'Pace':
            pace = float(command[1])
            if extent:
                pause = pace / extent.number_of_bells
            else:
                pause = pace / MAX_BELLS
        elif command[0] == "Load":
            method = Method(app_path + '/data/' + command[1] + '.mcf')
            extent = Extent(method, extent_id = command[2], cover = (command[3] == 'cover'), intro_courses = int(command[4]), extent_courses = int(command[5]), wait_learner = (command[6] == 'True'))
#            extent.dump()
            extent.to_mdf()
            pause = pace / extent.number_of_bells
        elif command[0] == "Play":
            bell = int(command[1])
            bells[bell - 1] = command[2] == "True"
        elif command[0] == "Rung":
            bell = int(command[1])
            bells_rung[bell - 1] = True
