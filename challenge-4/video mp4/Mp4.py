import sys
from pathlib import Path
import subprocess

def remove_audio(input_path: str):
    input_path = Path(input_path)
    output_path = input_path.with_name(input_path.stem + "_muted" + input_path.suffix)

    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-an",
        "-c:v", "copy",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)
    return str(output_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_audio.py <video.mp4>")
        sys.exit(1)
    out = remove_audio(sys.argv[1])
    print("Vidéo sans son :", out)
