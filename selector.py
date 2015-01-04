import subprocess
import argparse
import re

import av
import numpy as np
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Detect the sound of toppled over Club Mate bottles at 31c3 talks.')
parser.add_argument('file', help='Ogg/Opus audio file to search for sound of toppled over bottles.')
parser.add_argument('-b', '--begin', help='Start playback or analysis at specified time, e.g. 17m9s or 41s or 12392424t ("t" is libav\'s AV_TIME_BASE).')
parser.add_argument('-d', '--duration', default='1s', help='Limit playback or analysis to specified duration, e.g. 300ms or 20s')
parser.add_argument('-p', '--play', action='store_true', default=False, help='Play the specified audio file')
parser.add_argument('-n', '--no-analyze', action='store_true', default=False, help='Don\'t do spectrum (Fourier) analysis')
parser.add_argument('-v', '--verbose', action='count', default=0, help='Verboseness, e.g. -v: a little debug output -vvv: A LOT of debug output.')
args = parser.parse_args()


times = []
with open('audio/31c3-6240-en-Reproducible_Builds_opus.txt') as f:
    for l in f.readlines():
        m = re.match(r'^(\d+):(\d+)-(\d+):(\d+)   .*$', l)
        if m is None:
            continue

        start_minutes = int(m.group(1))
        start_secs    = int(m.group(2))
        end_minutes   = int(m.group(3))
        end_secs      = int(m.group(4))

        times.append((
            (start_minutes, start_secs, 0, 0),
            (end_minutes, end_secs, 0, 0),
        ))


# CONSTANTS
# http://ffmpeg-users.933282.n4.nabble.com/Duration-format-td935367.html
AV_TIME_BASE = av.time_base

# OPEN FILE
container = av.open(args.file)
audio_stream = [s for s in container.streams if s.type == 'audio'][0]
sample_rate = audio_stream.rate


######### MAIN LOOP #########
for time in times:
    minutes, seconds, milliseconds, ticks = time[0]

    # Seek to given time
    seek_to_secs = None
    seek_to_secs = 0
    seek_to_secs += float(ticks) / AV_TIME_BASE
    seek_to_secs += float(milliseconds) / 1000
    seek_to_secs += seconds
    seek_to_secs += 60 * minutes

    seek_to_ts = int(seek_to_secs * AV_TIME_BASE)

    if args.verbose >= 1:
        print('Seeking to:', seek_to_ts)
    container.seek(seek_to_ts)

    minutes, seconds, milliseconds, ticks = time[1]
    end_secs = 0
    end_secs += float(ticks) / AV_TIME_BASE
    end_secs += float(milliseconds) / 1000
    end_secs += seconds
    end_secs += 60 * minutes
    duration = end_secs - seek_to_secs

    # `audio_stream.rate` is 48000 -- 48kHz sampling rate
    sample_length = audio_stream.rate * duration
    sample = np.zeros(sample_length, dtype='float32')
    i = 0

    # Load sound data
    for packet in container.demux(audio_stream):
        if i >= sample_length:
            break

        for frame in packet.decode():

            if args.verbose >= 3:
                print('dts:', frame.dts)
                print('pts:', frame.pts)
                print('time:', frame.time)
                print('time_base:', frame.time_base)

            # Skip to start
            if seek_to_secs is not None and frame.time < seek_to_secs:
                if args.verbose >= 3:
                    print('Skipping %.3f < %.3f' % (frame.time, seek_to_secs))
                continue

            # '<f4': 4-byte floats little endian
            frame_sample = np.fromstring(frame.planes[0].to_bytes(), dtype='<f4')

            # Make sure we don't go beyond the length of our sample buffer
            window_end = min(i + frame_sample.shape[0], sample_length)
            sample[i:window_end] = frame_sample[:window_end-i]
            i = window_end

    if not args.no_analyze:
        # Plot sound wave
        # plot(np.indices(sample.shape)[0]/48000, sample)
        # xlabel('time [s]')
        # # ylabel('amplitude [?]')
        # show()

        # Plot spectogram
        spectrogram = plt.specgram(sample)
        plt.title('Spectrogram')
        plt.show()
        continue

        # Plot frequencies (Fourier transform)
        fourier = np.fft.rfft(sample)
        freq = np.fft.rfftfreq(sample.shape[0], d=1./sample_rate)

        # fourier2 = np.fft.rfft(sample2)

        fig, ax = plt.subplots()
        # ax.plot(freq, fourier2, color="blue", alpha=0.5) # half-transparant blue
        ax.plot(freq, fourier,  color="red", alpha=0.5) # half-transparant red
        # plot([freq, freq], [fourier, fourier2])
        ax.set_xlabel('frequency [Hz]')
        ax.set_ylabel('amplitude [?]')
        plt.show()

    # import pdb; pdb.set_trace()
    if args.play:
        import pyaudio
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paFloat32,
                        channels=1,
                        rate=48000,
                        output=True)
        stream.start_stream()

        # while data != '':
        stream.write(sample.tobytes())

        # stop stream
        stream.stop_stream()
        stream.close()

        # close PyAudio
        p.terminate()
