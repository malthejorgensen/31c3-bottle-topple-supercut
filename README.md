31c3 bottle topple supercut tool
================================
This is a tool to detect the sound of toppled over Club Mate bottles at 31c3
talks and create a supercut.

Installation and requirements
-----------------------------
Depends on _PyAudio_ which in turn depends on _PortAudio_.
PortAudio can be installed with homebrew on OS X: `brew install portaudio`.

And _PyAudio_ can be installed with the slightly hairy _pip_ command:

    pip install pyaudio --allow-external pyaudio --allow-unverified pyaudio

After that just do `pip install -r requirements.txt`.

Running
-------
The script `detector.py` will by default plot a spectogram of the sound file
given as its first argument. Giving the `--play` argument will play the sound
file as well. `--begin` and `--duration` can be used to specify a starting point
in the file and a duration to do the spectrogram on and/or play.
For a full list of options run: `python detector.py --help`

To-do list
----------
☑ Get sound stream from OPUS file  
☐ Detect bottle topple (with random forest?)  
☐ Create supercut from detected bottle topples  
