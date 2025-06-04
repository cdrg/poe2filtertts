import os
import re

import ffmpeg

def get_max_volume(filepath: str) -> float:
    """
    Get the maximum volume of an audio file using ffmpeg volumedetect.
    Inverse of return value used with ffmpeg .volume(volume="x.xdB") filter to increase file to 0db max peak.

    When used with "volume" guarantees that the entire file loudness is increased to 0db peak
    (dumb normalization), at the cost of audio quality.
    
    Args:
        filepath (str): ffmpeg-compatible audio file path.
    Returns:
        float: Maximum volume in dB from ffmpeg output.
    Raises:
        FFMpegExecuteError: If ffmpeg command fails to execute.
        ValueError: If max_volume could not be found in ffmpeg output.
    """
    if filepath.endswith(".pcm"): 
        # pcm files have no container with metadata, so we need to specify rate, channels, and format
        # Polly PCM output is 16000Hz, 1-channel, 16-bit signed little-endian
        input_stream: ffmpeg.AudioStream = ffmpeg.input(filepath, ar=16000, ac=1, f="s16le")
    else:
        input_stream: ffmpeg.AudioStream = ffmpeg.input(filepath)

    output_stream: ffmpeg.dag.OutputStream = input_stream.volumedetect().output(
                                                                    filename=os.devnull, f="null")
    # for some reason the output is in stderr instead of stdout
    stderr: str = output_stream.run(capture_stderr=True)[1].decode('utf-8')

    max_volume_match: re.Match[str]|None = re.search(r"max_volume:\s*(-?\d+(\.\d+)?) dB", stderr)
    if max_volume_match:
        max_volume: float = float(max_volume_match.group(1))
        return max_volume
    else:
        raise ValueError("Could not find max_volume in ffmpeg output.")