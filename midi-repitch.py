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
CHUNK_SIZE = 2048
SAMPLE_FADE = 2048
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
last_val = 0

clear_list = True

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
  global clear_list
  if type == 144:
    print(f"note on: {musx.pitch(keynum)}")
    clear_list = True
    notes_on += 1
  if type == 128:
    print(f"note off: {musx.pitch(keynum)}")
    to_remove.append(keynum)
    notes_on -= 1
  if notes_on < 0: notes_on = 0
  print("notes on:", notes_on)

def half_speed_audio(start_flag, input_list, output_list):
  # Just wait for keyboard interrupt,
  # everything else is handled via the input callback.
  if start_flag:
    input_data = i_stream.read(CHUNK_SIZE + 1, exception_on_overflow=False)
  else:
    input_data = i_stream.read(CHUNK_SIZE, exception_on_overflow=False)

  print("read_availability: ", i_stream.get_read_available())
  print("input latency: ", i_stream.get_input_latency())
  print("output latency: ", i_stream.get_output_latency())

  dt = np.int16
  input_samples = np.frombuffer(input_data, dtype=dt)

  for sample in input_samples:
    input_list.append(sample)

  input_samples = np.array(input_list[:CHUNK_SIZE + 1])

  # interpolate samples to be double in length = half speed = lower pitch
  output_samples = np.interp(np.linspace(0, CHUNK_SIZE, 2*CHUNK_SIZE + 1), np.arange(CHUNK_SIZE + 1), input_samples)
  
  for sample in output_samples[:CHUNK_SIZE * 2]:
    output_list.append(sample)
  output_samples = np.array(output_list[:CHUNK_SIZE])

  resampled_data = output_samples.astype(dt).tobytes()
  o_stream.write(resampled_data)

  # last_val = input_list[CHUNK_SIZE]
  input_list = input_list[CHUNK_SIZE:]
  output_list = output_list[CHUNK_SIZE:]

  start_flag = False

midiin.set_callback(master_midi_callback)

# code taken from https://github.com/SpotlightKid/python-rtmidi/blob/master/examples/basic/midiin_callback.py 
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
    
    # for output_list in output_lists:

      # add samples to each part
    if notes_on != 0:
      print(f"starting audio | last_val:{last_val}")
      for sample in output_samples[:CHUNK_SIZE * 2]:
        output_list.append(sample)
      if last_val == 0:
      # TODO: fade_in on the first note!
        print("starting note!")
        for i in range(SAMPLE_FADE):
          output_list[i] *= (i / SAMPLE_FADE)
          clear_list = False

    output_samples = np.array(output_list[:CHUNK_SIZE])

    resampled_data = output_samples.astype(dt).tobytes()
    o_stream.write(resampled_data)
    output_list = output_list[CHUNK_SIZE:]

    if clear_list and last_val != 0:
      # TODO: fade_through on the new pitch
      for i in range(SAMPLE_FADE):
        output_list[len(output_list) - (i + 1)] *= (i / SAMPLE_FADE)
      print("ending notes")
      output_list.clear()
      clear_list = False

    # last_val = input_list[CHUNK_SIZE]
    last_val = notes_on
    input_list = input_list[CHUNK_SIZE:]

    start_flag = False

except KeyboardInterrupt:
    print('')
finally:
    print("Exit.")
    midiin.close_port()
    del midiin

# stuff


# TODO: Fade in and out on new note trigger:

# Consider the three cases: new_note, retrigger, note_release
# Possible logic when these occur:
# - new_note: note_val == 1, last_note = 0 (should fade in!)
# - retrigger: note_val > 1, last_note > 0 (fade out current, clear remaining out)
# - note_release: note_val = 0, last_note > 0 (fade last portion of the stream!)

# on any note_on trigger, should the values in!