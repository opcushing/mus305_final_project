# MUS 305 Final Project: Live Disklavier Octave Repitch

This python program live repitches a Disklavier or MIDI device that also produces audio. 

## How to use

- Install the required libraries: musx, rtmidi, pyaudio, numpy
- Change the line of code that sets the midi device.
- Make sure MIDI Device is plugged in and that you set your computer's setting to the desired sound input.
- Start the program and enjoy!

## Future ideas / implementations:

- Currently the effect is monophonic, meaning one audio stream is repitched at a time. A future implementation might create multiple streams of repitched audio to produce a more layered effect.
- Ability to change the repitching amount would be desired. Currently, the program only repitches down an octave, but it would be cool to change this amount.
- Ability to dry/wet mix between the incoming audio and the repitched audio.
