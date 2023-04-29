import sys
import time

import pyaudio
# import wave

# import asyncio

import rtmidi
import musx

import numpy as np

FORMAT = pyaudio.paInt16
CHANNELS = 1 if sys.platform == 'darwin' else 2
RATE = 44100
CHUNK_SIZE = 1024
# SAMPLE_FADE = CHUNK_SIZE
RECORD_SECONDS = 5

p = pyaudio.PyAudio()

midiin = rtmidi.MidiIn()
inports = midiin.get_ports()
print("available ports:", inports)

# midiin.open_port(inports.index('IAC Driver Bus 1'))
midiin.open_port(inports.index('LPK25'))
print(midiin.is_port_open())

# open a master audio stream to record from

i_stream = p.open(format=p.get_format_from_width(2),
                channels=1 if sys.platform == 'darwin' else 2,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE)

o_stream = p.open(format=p.get_format_from_width(2),
                channels=1 if sys.platform == 'darwin' else 2,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE)

# Should support up to maybe 8-16 notes?
# Create a unique_id / index for each of the notes that is on / triggered

# def start_audio(id: int):
#   pass
# def stop_audio(id: int):
#   pass

# need a way to give each function a unique_id. when the corresponding note_off 
# is called, the audio stream for that note should be stopped!

notes_on = 0
notes_on_prev = 0

note_on_trigger = True

start_flag = True
input_list = []
output_list = []

to_remove = []

def master_midi_callback(message, data):
  # print("midi callback: message =", message, ", data =", data)
  note_on_or_off = message[0]
  # print(note_on_or_off)
  type = note_on_or_off[0]
  keynum = note_on_or_off[1]
  global notes_on
  global note_on_trigger
  if type == 144:
    print(f"note on: {musx.pitch(keynum)}")
    note_on_trigger = True
    notes_on += 1
  if type == 128:
    print(f"note off: {musx.pitch(keynum)}")
    to_remove.append(keynum)
    notes_on -= 1
  if notes_on < 0: notes_on = 0
  print("notes on:", notes_on)

midiin.set_callback(master_midi_callback)

# Loop until exception taken from https://github.com/SpotlightKid/python-rtmidi/blob/master/examples/basic/midiin_callback.py 
print("Started application. Press Control-C to exit.")
try:
  while True:
    if start_flag:
      input_data = i_stream.read(CHUNK_SIZE + 1, exception_on_overflow=False)
    else:
      input_data = i_stream.read(CHUNK_SIZE, exception_on_overflow=False)

    # print("read_availability: ", i_stream.get_read_available())
    # print("input latency: ", i_stream.get_input_latency())
    # print("output latency: ", i_stream.get_output_latency())

    dt = np.int16
    input_samples = np.frombuffer(input_data, dtype=dt)

    for sample in input_samples:
      input_list.append(sample)

    input_samples = np.array(input_list[:CHUNK_SIZE + 1])

    # interpolate samples to be double in length = half speed = lower pitch
    output_samples = np.interp(np.linspace(0, CHUNK_SIZE, 2*CHUNK_SIZE + 1), np.arange(CHUNK_SIZE + 1), input_samples)
    
    # TODO: Fade in and out on new note trigger:

    # Consider the three cases: new_note, retrigger, note_release
    # Possible logic when these occur:
    # - new_note: notes_on == 1, notes_on_prev = 0 (should fade in!)
    # - retrigger: notes_on > 1, notes_on_prev > 0 (fade out current, clear remaining out)
    # - note_release: notes_on = 0, notes_on_prev > 0 (fade last portion of the stream!)

    new_note = note_on_trigger and notes_on_prev == 0 # fade in (clear?)
    retrigger = note_on_trigger and notes_on_prev > 0 # fade out remaining, clear, fade in
    note_release = notes_on == 0 and notes_on_prev > 0 # fade out remaining

    # on any note_on trigger, should the values in!

    if notes_on > 0: # if a note is currently playing
      # print(f"audio streaming | curr: {notes_on} | prev:{notes_on_prev}")
      if note_on_trigger: # ATTACK
        # fade through or in, clear out remaining stream.

        # crossface the values!
        fade_chunk = []
        curr_chunk = output_list[:CHUNK_SIZE]
        if len(curr_chunk) < CHUNK_SIZE:
          curr_chunk = [0] * CHUNK_SIZE # crossfade from silence!
        for i in range(CHUNK_SIZE):
          orig_portion = curr_chunk[i] * ((CHUNK_SIZE - i) / CHUNK_SIZE)
          new_portion = output_samples[i] * (i / CHUNK_SIZE)
          # print(orig_portion + new_portion)
          fade_chunk.append(orig_portion + new_portion)
        for val in output_samples[CHUNK_SIZE:]:
          fade_chunk.append(val)
        output_list.clear()
        print(f'len(output_list): {len(output_list)}')
        print(f'len(fade_chunk): {len(fade_chunk)}')
        print(f'len(output_samples): {len(output_samples)}')
        for sample in fade_chunk:
          output_list.append(sample)
        note_on_trigger = False
      else: # SUSTAIN
        # print("sustain")
        for sample in output_samples[:CHUNK_SIZE * 2]:
          output_list.append(sample)
    elif notes_on_prev > 0: # RELEASE
      # fade_out last portion
      for i in range(CHUNK_SIZE):
        # print("idx:", len(output_list) - (i + 1))
        if len(output_list) > 0:
          output_list[len(output_list) - (i + 1)] *= (i / CHUNK_SIZE)

    output_samples = np.array(output_list[:CHUNK_SIZE])

    resampled_data = output_samples.astype(dt).tobytes()
    o_stream.write(resampled_data)
    output_list = output_list[CHUNK_SIZE:]

    # last_val = input_list[CHUNK_SIZE]
    notes_on_prev = notes_on
    input_list = input_list[CHUNK_SIZE:]

    start_flag = False

except KeyboardInterrupt:
    print('')
finally:
    print("Exit.")
    midiin.close_port()
    del midiin

# def half_speed_audio(start_flag, input_list, output_list):
#   # Just wait for keyboard interrupt,
#   # everything else is handled via the input callback.
#   if start_flag:
#     input_data = i_stream.read(CHUNK_SIZE + 1, exception_on_overflow=False)
#   else:
#     input_data = i_stream.read(CHUNK_SIZE, exception_on_overflow=False)

#   print("read_availability: ", i_stream.get_read_available())
#   print("input latency: ", i_stream.get_input_latency())
#   print("output latency: ", i_stream.get_output_latency())

#   dt = np.int16
#   input_samples = np.frombuffer(input_data, dtype=dt)

#   for sample in input_samples:
#     input_list.append(sample)

#   input_samples = np.array(input_list[:CHUNK_SIZE + 1])

#   # interpolate samples to be double in length = half speed = lower pitch
#   output_samples = np.interp(np.linspace(0, CHUNK_SIZE, 2*CHUNK_SIZE + 1), np.arange(CHUNK_SIZE + 1), input_samples)
  
#   for sample in output_samples[:CHUNK_SIZE * 2]:
#     output_list.append(sample)
#   output_samples = np.array(output_list[:CHUNK_SIZE])

#   resampled_data = output_samples.astype(dt).tobytes()
#   o_stream.write(resampled_data)

#   # last_val = input_list[CHUNK_SIZE]
#   input_list = input_list[CHUNK_SIZE:]
#   output_list = output_list[CHUNK_SIZE:]

#   start_flag = False