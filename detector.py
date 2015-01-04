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

# CONSTANTS
# http://ffmpeg-users.933282.n4.nabble.com/Duration-format-td935367.html
AV_TIME_BASE = av.time_base

def parse_time(time_str):
    m = re.match(r'^((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?((?P<milliseconds>\d+)ms)?((?P<ticks>\d+)t)?$', time_str)
    if m is None or time_str == '':
        raise Exception('Could not parse time: Must be of the form [MINUTESm][SECONDSs][MILLISECONDSms][TICKSt], e.g. "30m11s", "28s", "12392424t" or "4m300ms90090t".')

    minutes, seconds, milliseconds, ticks = 0, 0, 0, 0

    if m.group('ticks') is not None:
        ticks = int(m.group('ticks'))
    if m.group('milliseconds') is not None:
        milliseconds = int(m.group('milliseconds'))
    if m.group('seconds') is not None:
        seconds = int(m.group('seconds'))
    if m.group('minutes') is not None:
        minutes = int(m.group('minutes'))

    return (minutes, seconds, milliseconds, ticks)


# OPEN FILE
container = av.open(args.file)
audio_stream = [s for s in container.streams if s.type == 'audio'][0]
sample_rate = audio_stream.rate

seek_to_secs = None
if args.begin is not None:
    try:
        minutes, seconds, milliseconds, ticks = parse_time(args.begin)
        print( parse_time(args.begin) )
    except Exception as e:
        print('Could not parse --begin argument: %s' % e)
        exit(1)

    seek_to_secs = 0
    seek_to_secs += float(ticks) / AV_TIME_BASE
    seek_to_secs += float(milliseconds) / 1000
    seek_to_secs += seconds
    seek_to_secs += 60 * minutes

    seek_to_ts = int(seek_to_secs * AV_TIME_BASE)

    if args.verbose >= 1:
        print('Seeking to:', seek_to_ts)
    container.seek(seek_to_ts)
    # audio_stream.seek(seek_to_ts)

if args.duration is not None:
    try:
        minutes, seconds, milliseconds, ticks = parse_time(args.duration)
    except Exception as e:
        print('Could not parse --duration argument: %s' % e)
        exit(1)

    duration = 0
    duration += float(ticks) / AV_TIME_BASE
    duration += float(milliseconds) / 1000
    duration += seconds
    duration += 60 * minutes

# `audio_stream.rate` is 48000 -- 48kHz sampling rate
sample_length = audio_stream.rate * duration
sample = np.zeros(sample_length, dtype='float32')
i = 0

# sample2_length = 48000 * 1 # 1 second worth of samples
# sample2 = np.zeros(sample2_length, dtype='float32')
# j = 0

if args.play:
    import pyaudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=48000,
                    output=True)
    stream.start_stream()


for packet in container.demux(audio_stream):
    if i >= sample.shape[0]:
        break

    # if j >= sample2.shape[0]:
    #     break

    for frame in packet.decode():

        if args.verbose >= 3:
            print('dts:', frame.dts)
            print('pts:', frame.pts)
            print('time:', frame.time)
            print('time_base:', frame.time_base)

        if seek_to_secs is not None and frame.time < seek_to_secs:
            if args.verbose >= 3:
                print('Skipping %.3f < %.3f' % (frame.time, seek_to_secs))
            continue

        if args.play:
            stream.write(frame.planes[0].to_bytes())

        # '<f4': 4-byte floats little endian
        frame_sample = np.fromstring(frame.planes[0].to_bytes(), dtype='<f4')

        if i != sample_length:
            if i + frame_sample.shape[0] > sample_length:
                sample[i:sample_length] = frame_sample[:i-sample_length]
                i = sample_length
                break
            else:
                sample[i:i+frame_sample.shape[0]] = frame_sample
                i += frame_sample.shape[0]
        # else:
        #     if j + frame_sample.shape[0] > sample2_length:
        #         sample[j:sample2_length] = frame_sample[:j-sample2_length]
        #         j = sample2_length
        #         break
        #     else:
        #         sample2[j:j+frame_sample.shape[0]] = frame_sample
        #         j += frame_sample.shape[0]


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
    exit()

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

if args.play:
    # stop PyAudio output stream and close PyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()
