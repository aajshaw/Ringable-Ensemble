import configparser
import PySimpleGUI as sg

def add_intro(rows, bells, intro_hs_bs_length = 1):
    for intro in range(intro_hs_bs_length):
        for r in range(2):
            rows.insert(0, [b + 1 for b in range(bells)])

    return rows

def add_half_round(rows, bells):
    if len(rows) == 0:
        rows.append([ndx + 1 for ndx in range(bells)])
    else:
        row = rows[len(rows) - 1]
        rows.append([b for b in row])

    return rows

def add_round(rows, bells):
    for r in range(2):
#        if len(rows) == 0:
#            rows.append([ndx + 1 for ndx in range(bells)])
#        else:
#            row = rows[len(rows) - 1]
#            rows.append([b for b in row])
        rows = add_half_round(rows, bells)

    return rows

def add_plain(rows, bells, length):
    apply(rows, bells, tracks, length)
    apply(rows, bells, plain, length)

    return rows

def add_single(rows, bells, length):
    apply(rows, bells, tracks, length)
    apply(rows, bells, single, length)

    return rows

def add_bob(rows, bells, length):
    apply(rows, bells, tracks, length)
#    row = rows[len(rows) - 1]
#    row.insert(0, 'B')
    apply(rows, bells, bob, length)

    return rows

def apply(rows, bells, work, length):
    prev = len(rows) - 1

#    print('apply(): length of rows = ' + str(len(rows)) + ' length = ' + str(length))

    for ndx in range(len(work[0])):
        if length > len(rows):
            rows.append([None for X in range(bells)])

#    print('New length of rows is ' + str(len(rows)))

    for track in range(bells):
        if prev < 0:
            bell = track + 1
        else:
            bell = rows[prev][track]
        curr = prev + 1
        for t in work[track]:
            if curr < length:
#                print(curr, rows[curr])
                rows[curr][t - 1] = bell
                curr += 1

definition = configparser.ConfigParser(inline_comment_prefixes=';')

tcf = sg.PopupGetFile('Select Touch Composition file', file_types = (('Touch Compositions', '*.tcf'),))
if tcf == None:
    exit()
definition.read(tcf)

print('Method name - ' + definition['INFO']['name'])
print(f'There are {definition["INFO"]["definitions"]} extent definitions')

tracks = {}
for key in definition['TRACKS']:
    print(key, definition['TRACKS'][key])
    tracks[int(key) - 1] = [int(v) for v in definition['TRACKS'][key].split()]
#print(tracks)

plain = {}
for key in definition['PLAIN']:
    plain[int(key) - 1] = [int(v) for v in definition['PLAIN'][key].split()]

bob = {}
for key in definition['BOB']:
    bob[int(key) - 1] = [int(v) for v in definition['BOB'][key].split()]
#print('BOB ' + str(bob))

single = {}
for key in definition['SINGLE']:
    single[int(key) - 1] = [int(v) for v in definition['SINGLE'][key].split()]
#print('SINGLE ' + str(single))

touches = definition['TOUCHES']
for t in touches:
    print(t, touches[t])

touches = []
touch_lengths = []
for k in definition['TOUCHES'].keys():
    touches.append(k)
    touch_lengths.append(int(definition['TOUCHES'][k]))

#touch = touches[0]
#touch_length = touch_lengths[0] + 2
d = definition['DEF-3']
extent = d['extent']
extent_length = int(d['length'])

rows = []
#rows = add_round(rows, 5)
#rows = add_plain(rows, 5)
#rows = add_single(rows, 5)
#rows = add_bob(rows, 5)
#rows = add_plain(rows, 5)
#rows = add_plain(rows, 5)
#rows = add_plain(rows, 5)
#rows = add_single(rows, 5)
#rows = add_bob(rows, 5)
for lead in extent:
    if lead in ('p', 'P'):
        rows = add_plain(rows, 5, extent_length)
    elif lead in ('b', 'B'):
        rows = add_bob(rows, 5, extent_length)
    elif lead in ('s', 'S'):
        rows = add_single(rows, 5, extent_length)
#    else:
#        sg.PopupError("Invalid lead type '" + lead + "'", title = 'Invalid Lead')
#        exit()
# If the extent ended on a back stroke add the extra half round
if len(rows) % 2 != 0:
    rows = add_half_round(rows, 5)
rows = add_round(rows, 5)

# Add the intro
rows = add_intro(rows, 5)

print('----------')
row = 1
for r in rows:
    print(row, r)
    row += 1
