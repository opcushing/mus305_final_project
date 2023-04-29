
import sys
import pyaudio
import numpy as np
import time

RECORD_SECONDS = 5
CHUNK_SIZE = 1024
RATE = 44100

p = pyaudio.PyAudio()
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

# print(p.get_device_info_by_index(0)['defaultSampleRate'])
input_list = []
output_list = []

start_flag = True

last_val = 0

start = time.time()

print('* recording')
# for i in range(0, int(RATE / CHUNK_SIZE * RECORD_SECONDS)):
while True:
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

  last_val = input_list[CHUNK_SIZE]
  input_list = input_list[CHUNK_SIZE:]
  output_list = output_list[CHUNK_SIZE:]

  start_flag = False

end = time.time()

print(end - start)

print('* done')

o_stream.close()
p.terminate()