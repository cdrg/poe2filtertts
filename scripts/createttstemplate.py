"""
Create a json TTS audio file list template with default entries from an existing TTS directory.
Should only needed to be run once, when creating a template for the first time.
Template should be fixed as necessary by hand after creation.

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


def main():
    '''
    Create a json TTS audio file list template with default entries from an existing TTS directory.

    Returns:
        exit_val (int): 0 on success, 1 on error
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", help="the input directory to crawl", default=os.getcwd())
    parser.add_argument("-f", "--file", help="the name of the output template json file", default="template.json")
    args = parser.parse_args()

    if not os.path.exists(args.directory):
        print(f"Error: directory '{args.directory}' does not exist.")
        return 1

    template = []

    entry_count = 0
    # create template data structure from existing directory structure
    for root, _, files in os.walk(args.directory, topdown=False):
        for filename in files:
            if filename.endswith(".mp3"):
                # path relative to sounds dir, remove leading path separator if present
                entry_path = os.path.join(root.split("sounds")[1], filename).removeprefix("/")

                entry_tts_text = filename.removesuffix(".mp3")
                # move 'rare' to front of text if it ends with 'rare'
                if entry_tts_text.endswith(" rare"):
                    entry_tts_text = "rare " + entry_tts_text.removesuffix(" rare")
                 # move 'magic' to front of text if it ends with 'magic'
                if entry_tts_text.endswith(" magic"):
                    entry_tts_text = "magic " + entry_tts_text.removesuffix(" magic")
                # remove redundant currency prefixes and suffixes such as "orb of " or " orb"
                entry_tts_text = entry_tts_text.replace("orb of ", "")
                entry_tts_text = entry_tts_text.replace("scroll of ", "")
                entry_tts_text = entry_tts_text.replace(" orb", "")

                entry_ssml_text = ""
                # create fast rate prosidy ssml if tts text is multiple words
                if " " in entry_tts_text:
                    entry_ssml_text = "<prosody rate='fast'>" + entry_tts_text + "</prosody>"
                # fix pronunciation if (ssml) text contains '1h' or '2h'
                if "1h" in entry_ssml_text:
                    entry_ssml_text = entry_ssml_text.replace("1h", "<say-as interpret-as='characters'>1h</say-as>")
                if "2h" in entry_ssml_text:
                    entry_ssml_text = entry_ssml_text.replace("2h", "<say-as interpret-as='characters'>2h</say-as>")

                template.append((entry_path, entry_tts_text, entry_ssml_text))
                entry_count += 1
                if entry_count > 1:
                    print("\033[1A", end="\x1b[2K")
                print(f"Read entry {entry_count}: {template[-1]}", flush=True)

    # create json from template data structure
    template_json = json.dumps(template, indent=4)

    # output json to file
    try:
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(template_json)
    except IOError as e:
        print(f"{type(e)}: {e}")
        return 1

    print(f"Successfully created template file '{args.file}' with {entry_count} entries.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
