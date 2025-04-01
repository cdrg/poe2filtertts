"""
Create a soundpack set of TTS mp3 files from a template json file using AWS Polly.

For safety, a "sounds" subdirectory must already exist in specified output directory.

AWS boto3 package and configured AWS credentials required.

AWS free tier includes a generous amount of free Polly usage for the first year, 
and is inexpensive thereafter.

https://docs.aws.amazon.com/polly/latest/dg/API_Voice.html

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

from contextlib import closing
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError


def main():
    '''
    Create a soundpack set of TTS mp3 files from a template json file, using AWS Polly.

    Returns:
        exit_val (int): 0 on success, 1 on error
    '''

    valid_voices = ["Aditi", "Amy", "Astrid", "Bianca", "Brian", "Camila", "Carla", "Carmen", "Celine", "Chantal",
                    "Conchita", "Cristiano", "Dora", "Emma", "Enrique", "Ewa", "Filiz", "Gabrielle", "Geraint",
                    "Giorgio", "Gwyneth", "Hans", "Ines", "Ivy", "Jacek", "Jan", "Joanna", "Joey", "Justin", "Karl",
                    "Kendra", "Kevin", "Kimberly", "Lea", "Liv", "Lotte", "Lucia", "Lupe", "Mads", "Maja", "Marlene",
                    "Mathieu", "Matthew", "Maxim", "Mia", "Miguel", "Mizuki", "Naja", "Nicole", "Olivia", "Penelope",
                    "Raveena", "Ricardo", "Ruben", "Russell", "Salli", "Seoyeon", "Takumi", "Tatyana", "Vicki",
                    "Vitoria", "Zeina", "Zhiyu", "Aria", "Ayanda", "Arlet", "Hannah", "Arthur", "Daniel", "Liam",
                    "Pedro", "Kajal", "Hiujin", "Laura", "Elin", "Ida", "Suvi", "Ola", "Hala", "Andres", "Sergio",
                    "Remi", "Adriano", "Thiago", "Ruth", "Stephen", "Kazuha", "Tomoko", "Niamh", "Sofie", "Lisa",
                    "Isabelle", "Zayd", "Danielle", "Gregory", "Burcu", "Jitka", "Sabrina"]

    polly_engine = "standard"
    polly_outputformat = "mp3"

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
    args = parser.parse_args()

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

    polly_client = Session(profile_name="AWSUser").client('polly')

    with open(args.file, encoding="utf-8") as f:
        try:
            template = json.load(f)
        except (JSONDecodeError, UnicodeDecodeError) as e:
            print(f"{type(e)}: {e}")
            return 1

    created_count = 0
    skipped_count = 0

    # for each template entry that doesn't already exist as a file, call AWS Polly to create
    # the TTS audio object, then output the returned object to the specified file
    for item in template:
        file_partialpath = item[0]
        tts_text = item[1]
        ssml_text = item[2]

        file_fullpath = os.path.join(sounds_directory, file_partialpath)
        if not os.path.exists(file_fullpath):
            # need to create directory (and intermediate) if they don't exist
            if not os.path.exists(os.path.dirname(file_fullpath)):
                os.makedirs(os.path.dirname(file_fullpath), mode=0o755, exist_ok=True)

            # if SSML text exists, set texttype to ssml and use ssml text instead of plain tts text
            if ssml_text:
                polly_texttype = "ssml"
                tts_text = ssml_text
            else:
                polly_texttype = "text"

            try:
                response = polly_client.synthesize_speech(Text=tts_text, VoiceId=args.voice,
                                                          TextType=polly_texttype, Engine=polly_engine,
                                                          OutputFormat=polly_outputformat)
            except (BotoCoreError, ClientError) as e:
                print(f"{type(e)}: {e}")
                print(f"Template item: {item}")
                print(f"Call: synthesize_speech({tts_text}, {args.voice}, {polly_texttype}, "\
                      f"{polly_engine}, {polly_outputformat})")
                return 1

            if "AudioStream" in response:
                # use closing to ensure that the close method of the stream is called after the with finishes
                with closing(response["AudioStream"]) as stream:
                    try:
                        with open(file_fullpath, "wb") as f:
                            f.write(stream.read())
                            created_count += 1
                            if created_count > 1:
                                print("\033[1A", end="\x1b[2K")
                            print(f"Created file {created_count}: {file_fullpath}", flush=True)
                    except IOError as e:
                        print(f"{type(e)}: {e}")
                        return 1
            else:
                print("Error: No audiostream in AWS Polly response")
                return 1
        else:
            skipped_count += 1

    print(f"Successfully finished. {created_count} file(s) created and {skipped_count} existing file(s) skipped.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
