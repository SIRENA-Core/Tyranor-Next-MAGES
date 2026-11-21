"""Convert the Bink 2 movies of STEINS;GATE (Steam) into H.264/AAC MP4 files that the engine's FFmpeg can play
(FFmpeg has no Bink 2 video decoder). The video is decoded with the game's own bink2w32.dll (bink2dump.exe, 32-bit),
the audio is read from the .bk2 by ffmpeg (Bink audio is supported). Output files keep the original names, so the
profile's movie list stays the same; FFmpeg detects the container from the content.

usage: python sg_convert_bink2.py <game dir> <movie subdir, e.g. USRDIR/movie/1920x1080> <out dir> [names...]
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(HERE, "bink2dump", "bink2dump.exe")  # build with bink2dump/build.bat


def convert(dll, src, dst):
    info = subprocess.run([DUMP, dll, src, "info"], capture_output=True, text=True)
    if info.returncode != 0:
        raise RuntimeError(info.stderr.strip())
    w, h, frames, rate, div = info.stdout.split()
    dump = subprocess.Popen([DUMP, dll, src], stdout=subprocess.PIPE)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-r", f"{rate}/{div}", "-i", "-",
           "-i", src, "-map", "0:v", "-map", "1:a?",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-g", "60",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-f", "mp4", dst]
    enc = subprocess.run(cmd, stdin=dump.stdout)
    dump.stdout.close()
    dump.wait()
    if enc.returncode != 0 or dump.returncode != 0:
        raise RuntimeError(f"ffmpeg {enc.returncode}, dump {dump.returncode}")
    return int(frames)


def main():
    game, sub, out = sys.argv[1:4]
    only = {n.lower() for n in sys.argv[4:]}
    dll = os.path.join(game, "bink2w32.dll")
    src_dir = os.path.join(game, sub)
    os.makedirs(out, exist_ok=True)
    for name in sorted(os.listdir(src_dir)):
        src = os.path.join(src_dir, name)
        if only and name.lower() not in only:
            continue
        with open(src, "rb") as f:
            if f.read(3) != b"KB2":
                continue  # Bink 1 plays as it is
        dst = os.path.join(out, name)
        frames = convert(dll, src, dst)
        print(f"{name}: {frames} frames -> {os.path.getsize(dst) // 1024} KiB", flush=True)


if __name__ == "__main__":
    main()
