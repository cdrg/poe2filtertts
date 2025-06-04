"""
Create a soundpack set of TTS mp3 files from a template json file using AWS Polly.

For safety, a "sounds" subdirectory must already exist in specified output directory.

AWS boto3 package and configured AWS credentials required.

AWS free tier includes a generous amount of free Polly usage for the first year, 
and is inexpensive thereafter.

https://docs.aws.amazon.com/polly/latest/dg/API_Voice.html

---

template item json format: {path, tts_text, ssml_text}

path: the relative file path to the sounds dir including all subfolders, filename, extension (.mp3)
    file name should start with the full canonical name of the item, class, etc, then any modifiers  
tts_text: the actual text to be TTS read, in plain text; 
    for in-game clarity, can be completely different than the filename
ssml_text: (optional) SSML marked up text, empty string if none
"""

import sys
import os
import argparse
import json
from json import JSONDecodeError
import tempfile

import ffmpeg
from ffmpeg import FFMpegExecuteError
from contextlib import closing
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from mypy_boto3_polly.client import PollyClient
import ttsutil

def main() -> int:
    '''Create a soundpack set of TTS mp3 files from a template json file, using AWS Polly.

    Returns:
        (int): 0 on success, 1 on error
    '''

    valid_voices: list[str] = ["Aditi", "Amy", "Astrid", "Bianca", "Brian", "Camila", "Carla", "Carmen", "Celine", "Chantal",
                    "Conchita", "Cristiano", "Dora", "Emma", "Enrique", "Ewa", "Filiz", "Gabrielle", "Geraint",
                    "Giorgio", "Gwyneth", "Hans", "Ines", "Ivy", "Jacek", "Jan", "Joanna", "Joey", "Justin", "Karl",
                    "Kendra", "Kevin", "Kimberly", "Lea", "Liv", "Lotte", "Lucia", "Lupe", "Mads", "Maja", "Marlene",
                    "Mathieu", "Matthew", "Maxim", "Mia", "Miguel", "Mizuki", "Naja", "Nicole", "Olivia", "Penelope",
                    "Raveena", "Ricardo", "Ruben", "Russell", "Salli", "Seoyeon", "Takumi", "Tatyana", "Vicki",
                    "Vitoria", "Zeina", "Zhiyu", "Aria", "Ayanda", "Arlet", "Hannah", "Arthur", "Daniel", "Liam",
                    "Pedro", "Kajal", "Hiujin", "Laura", "Elin", "Ida", "Suvi", "Ola", "Hala", "Andres", "Sergio",
                    "Remi", "Adriano", "Thiago", "Ruth", "Stephen", "Kazuha", "Tomoko", "Niamh", "Sofie", "Lisa",
                    "Isabelle", "Zayd", "Danielle", "Gregory", "Burcu", "Jitka", "Sabrina"]

    # 'arb'|'cmn-CN'|'cy-GB'|'da-DK'|'de-DE'|'en-AU'|'en-GB'|'en-GB-WLS'|'en-IN'|'en-US'|'es-ES'|'es-MX'|
    # 'es-US'|'fr-CA'|'fr-FR'|'is-IS'|'it-IT'|'ja-JP'|'hi-IN'|'ko-KR'|'nb-NO'|'nl-NL'|'pl-PL'|'pt-BR'|
    # 'pt-PT'|'ro-RO'|'ru-RU'|'sv-SE'|'tr-TR'|'en-NZ'|'en-ZA'|'ca-ES'|'de-AT'|'yue-CN'|'ar-AE'|'fi-FI'|
    # 'en-IE'|'nl-BE'|'fr-BE'|'cs-CZ'|'de-CH'|'en-SG'
    #polly_language_code: str = "en-US" 
    polly_engine: str = "standard" # standard | neural | long-form | generative
    polly_outputformat: str = "mp3" # mp3 | ogg_vorbis | pcm

    parser = argparse.ArgumentParser()
    parser.add_argument("voice",
                        help="AWS Polly voice ID to use",
                        choices=valid_voices)
    parser.add_argument("-f", "--file",
                        help="the name of the input json template file",
                        default="template.json")
    parser.add_argument("-d", "--directory",
                        help="the output directory containing a 'sounds' subdirectory "\
                            "to create the directory structure and tts files in",
                        default=os.getcwd())
    args: argparse.Namespace = parser.parse_args()

    if polly_outputformat == "mp3":
        input_ext: str = ".mp3"
    elif polly_outputformat == "ogg_vorbis":
        input_ext: str = ".ogg"
    elif polly_outputformat == "pcm":
        input_ext: str = ".pcm"
    else:
        print(f"Error: Invalid Polly output format '{polly_outputformat}'")
        return 1

    sounds_directory: str = os.path.join(args.directory, "sounds")

    if not os.path.exists(args.file):
        print(f"Error: template file '{args.file}' does not exist.")
        return 1
    if not os.path.exists(args.directory):
        print(f"Error: output directory '{args.directory}' does not exist.")
        return 1
    if not os.path.exists(sounds_directory):
        print(f"Error: required subdirectory '{sounds_directory}' does not exist.")
        return 1

    polly_client: PollyClient = Session(profile_name="AWSUser").client('polly')

    with open(args.file, encoding="utf-8") as f:
        try:
            template: list[dict[str, str]] = json.load(f)
        except (JSONDecodeError, UnicodeDecodeError) as e:
            print(f"{type(e)}: {e}")
            return 1

    created_count: int = 0
    skipped_count: int = 0

    # for each template entry that doesn't already exist as a file, call AWS Polly to create
    # the TTS audio object, then output the returned object to the specified file
    item: dict[str, str]
    for item in template:
        file_partialpath: str = item["path"]
        tts_text: str = item["tts_text"]
        ssml_text: str = item["ssml_text"]

        file_fullpath: str = os.path.join(sounds_directory, file_partialpath)
        # skip if file already exists
        if os.path.exists(file_fullpath):
            skipped_count += 1
            continue

        # need to create output directory (and intermediates) if they don't exist
        if not os.path.exists(os.path.dirname(file_fullpath)):
            os.makedirs(os.path.dirname(file_fullpath), mode=0o755, exist_ok=True)

        # if SSML text exists, set texttype to ssml and use ssml text instead of plain tts text
        if ssml_text:
            polly_texttype: str = "ssml"
            tts_text: str = ssml_text
        else:
            polly_texttype: str = "text"

        try:
            # omit polly_language_code for now to get the default
            response = (
                polly_client.synthesize_speech(Text=tts_text, VoiceId=args.voice, 
                                                TextType=polly_texttype, Engine=polly_engine,
                                                OutputFormat=polly_outputformat))
        except (BotoCoreError, ClientError) as e:
            print(f"{type(e)}: {e}")
            print(f"Template item: {item}")
            print(f"Call: synthesize_speech({tts_text}, {args.voice}, {polly_texttype}, "\
                    f"{polly_engine}, {polly_outputformat})")
            return 1

        if "AudioStream" not in response:
            print("Error: No AudioStream in AWS Polly response")
            return 1
        
        # use closing to ensure that the close method of the stream is called after the with finishes
        with closing(response["AudioStream"]) as stream:
            try:
                # Write the stream to a temporary file so we can postprocess it with ffmpeg.
                # delete=False so we don't have to worry about staying in the with context
                with tempfile.NamedTemporaryFile(suffix=(input_ext), delete=False) as f:
                    f.write(stream.read())
            except IOError as e:
                print(f"{type(e)}: {e}")
                return 1
            
        # Get the max db of the audio file with ffmpeg volumedetect so we can increase file volume.
        try:
            input_max_volume: float = ttsutil.get_max_volume(f.name)
        except (FFMpegExecuteError, ValueError) as e:
            print(f"{type(e)}: {e}")
            os.remove(f.name) # cleanup temp file if exiting early
            return 1     

        # Set ffmpeg input to the the temp file.
        # ffmpeg will intelligently handle format conversion based on the extension of the output file.
        # If input is pcm format, we need to specify rate, channels, format for ffmpeg
        # AWS Polly PCM output is 16000Hz, 1-channel, 16-bit signed little-endian
        if input_ext == ".pcm":
            input_stream: ffmpeg.AudioStream = ffmpeg.input(f.name, ar=16000, ac=1, f="s16le")
        else:
            input_stream: ffmpeg.AudioStream = ffmpeg.input(f.name)

        #TODO: set speech speed to hit a specific total audio duration, instead of guessing?
        #TODO: Check if selected AWS Polly voice supports SSML? Currently only using SSML voices.
        # If "prosody rate='fast'" is set in SSML text, simulate that with ffmpeg atempo filter.
        # AWS Polly SSML rate='fast' is ~150% (1.5) per experiments.
        #if "rate='fast'" in ssml_text:
        #    input_stream = input_stream.atempo(tempo=1.3)

        # Files must be as loud as possible to be consistently audible in-game.
        # If previously determined peak db is less than -0.5db, use ffmpeg volume filter 
        # to increase the file volume by the same amount, resulting in -0.5db peak.
        # Unfortunately, other ffmpeg filters such as loudnorm or dynaudnorm do not 
        # work well for our purposes, so we have to do this two-pass method.
        if input_max_volume < -0.5:
            volume_adjustment: float = -input_max_volume-0.5 # -0.5dB for clipping safety
            input_stream = input_stream.volume(volume=f"{volume_adjustment}dB")

        # Path of Exile is picky about VBR mp3, and ffmpeg seems to default to VBR output,
        # so force CBR with ab= (b:a). Add abr=1 option for fun (hybrid CBR/VBR).
        output_stream: ffmpeg.dag.OutputStream = input_stream.output(filename=file_fullpath, ab="48k", extra_options={"abr": 1})

        # Lastly, run ffmpeg.
        try:
            output_stream.run(quiet=True)
        except FFMpegExecuteError as e:
            print(f"{type(e)}: {e}")
            os.remove(f.name) # cleanup temp file if exiting early
            return 1
        
        # cleanup temporary file
        os.remove(f.name)
        
        created_count += 1
        if created_count > 1:
            print("\033[1A", end="\x1b[2K")
        print(f"Created file {created_count}/~{len(template)-skipped_count}: {file_fullpath}", flush=True)

    print(f"Successfully finished. {created_count} file(s) created and {skipped_count} existing file(s) skipped. {created_count+skipped_count} total.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
