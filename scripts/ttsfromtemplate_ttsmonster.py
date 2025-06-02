"""
Create a soundpack set of TTS mp3 files from a template json file using TTS.Monster.

For safety, a "sounds" subdirectory must already exist in specified output directory.

TTS.Monster API key must be set in environment variable TTSMONSTER_API_KEY 

TTS.Monster free tier includes 10000 characters per month.

https://docs.tts.monster/introduction

---

template item json format: {path, tts_text, ssml_text}

path: the relative file path including all folders, filename, extension (.mp3)
tts_text: the actual text to be TTS read, in plain text; for in-game clarity, 
    can be completely different than the filename
ssml_text: (optional) SSML marked up text, empty string if none
"""

import sys
import os
import argparse
import json
from json import JSONDecodeError
import tempfile

import requests
from requests.exceptions import HTTPError
import ffmpeg
import ttsmapi
from ttsmapi.exceptions import TTSMAPIError
import ttsutil

def main() -> int:
    '''Create a soundpack set of TTS mp3 files from a template json file, using TTS.Monster.

    Returns:
        (int): 0 on success, 1 on error
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument("voiceid",
                        help="TTS.Monster voice ID to use")
    parser.add_argument("-f", "--file",
                        help="the name of the input json template file",
                        default="template.json")
    parser.add_argument("-d", "--directory",
                        help="the output directory containing a 'sounds' subdirectory "\
                            "to create the directory structure and tts files in",
                        default=os.getcwd())
    args: argparse.Namespace = parser.parse_args()

    sounds_directory = os.path.join(args.directory, "sounds")

    if not os.path.exists(args.file):
        print(f"Error: template file '{args.file}' does not exist.")
        return 1
    if not os.path.exists(args.directory):
        print(f"Error: output directory '{args.directory}' does not exist.")
        return 1
    if not os.path.exists(sounds_directory):
        print(f"Error: required subdirectory '{sounds_directory}' does not exist.")
        return 1

    with open(args.file, encoding="utf-8") as f:
        try:
            template: list[dict[str, str]] = json.load(f)
        except (JSONDecodeError, UnicodeDecodeError) as e:
            print(f"{type(e)}: {e}")
            return 1

    try: 
       ttsm_apikey: str = os.environ['TTSMONSTER_API_KEY']
    except KeyError as e:
        print(f"{type(e)}: {e}")
        return 1

    try:
        ttsm_client: ttsmapi.Client = ttsmapi.Client(ttsm_apikey)
    except (TTSMAPIError, HTTPError) as e:
        print(f"{type(e)}: {e}")
        return 1

    created_count: int = 0
    skipped_count: int = 0

    # For each template entry that doesn't already exist as a file, call TTS.Monster API to create a TTS file, 
    # then retrieve the TTS file from the URL returned by the API.
    item: dict[str, str]
    for item in template:
        file_partialpath: str = item["path"]
        tts_text: str = item["tts_text"]
        ssml_text: str = item["ssml_text"] # TTS.Monster does not support SSML, but we may simulate some features

        file_fullpath: str = os.path.join(sounds_directory, file_partialpath)
        # skip if file already exists
        if os.path.exists(file_fullpath):
            skipped_count += 1
            continue

        # need to create output directory (and intermediates) if they don't exist
        if not os.path.exists(os.path.dirname(file_fullpath)):
            os.makedirs(os.path.dirname(file_fullpath), mode=0o755, exist_ok=True)

        try:
            response: dict = ttsm_client.generate(voice_id=args.voiceid, message=tts_text)
        except (TTSMAPIError) as e:
            print(f"{type(e)}: {e}")
            print(f"Template item: {item}")
            print(f"Call: generate({args.voiceid}, {tts_text})")
            return 1

        if "url" in response:
            # Retrieve the audio file with Requests to a tempfile. Unfortunately necessary because of 
            # the need to do two-pass ffmpeg processing. Otherwise ffmpeg could get the file itself.
            try:
                url_response: requests.Response = requests.get(response["url"])
                with tempfile.NamedTemporaryFile(suffix=os.path.splitext(response["url"])[1]) as f:
                    f.write(url_response.content)
                    try:
                        max_volume: float = ttsutil.get_max_volume(f.name)
                    except ValueError as e:
                        print(f"{type(e)}: {e}")
                        return 1

                    # Set ffmpeg input to the tempfile.
                    # ffmpeg will intelligently handle format conversion based on the extension of the output file.
                    input_stream: ffmpeg.AudioStream = ffmpeg.input(f.name)

                    # If "prosody rate='fast'" is set in SSML text, simulate that with ffmpeg atempo filter.
                    # AWS Polly SSML rate='fast' is ~150% (1.5) per experiments.
                    if "rate='fast'" in ssml_text:
                        input_stream = input_stream.atempo(tempo=1.3)

                    # Files must be as loud as possible to be consistently audible in-game.
                    # If previously determined peak db is less than -0.5db, use ffmpeg volume filter 
                    # to increase the file volume by the same amount, resulting in -0.5db peak.
                    # Unfortunately, other ffmpeg filters such as loudnorm or dynaudnorm do not 
                    # work well for our purposes.
                    if max_volume < -0.5:
                        volume_adjustment: float = -max_volume-0.5 # 0.5dB for clipping safety
                        input_stream = input_stream.volume(volume=f"{volume_adjustment}dB")

                    # Lastly, set the output file and run ffmpeg.
                    input_stream.output(filename=file_fullpath).run(quiet=True)
            except (IOError, HTTPError) as e:
                print(f"{type(e)}: {e}")
                return 1
        else:
            print("Error: No audio URL in TTS.Monster response")
            return 1

        created_count += 1
        if created_count > 1:
            print("\033[1A", end="\x1b[2K")
        print(f"Created file {created_count}/{len(template)}: {file_fullpath}. "
                f"Used: {response['characterUsage']}/10000c", flush=True)

    print(f"Successfully finished. {created_count} file(s) created and {skipped_count} "
          f"existing file(s) skipped.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
