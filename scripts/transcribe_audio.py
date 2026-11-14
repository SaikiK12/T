"""One audio file to plain text with faster-whisper on CPU (used by scripts/dig_podcasts.py).

ffmpeg decodes the file to 16 kHz mono float32 on a pipe, so any container works (mp3, m4a, wav). Runs under an
interpreter that has faster-whisper (not part of the lab's .venv): the lab keeps it in a separate tool environment.
MODEL defaults to "base.en" (about 8x real time on 4 cores); set WHISPER_MODEL=small for harder audio.

usage: <python with faster-whisper> scripts/transcribe_audio.py AUDIO OUT.txt
"""
import os
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

MODEL = os.environ.get("WHISPER_MODEL", "base.en")


def decode(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def main(audio, out):
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(decode(audio), vad_filter=True, beam_size=1)
    text = " ".join(s.text.strip() for s in segs)
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
