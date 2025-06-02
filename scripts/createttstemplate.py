"""
Create or update a json TTS audio file list template with default entries from an existing TTS directory.

Template file entires can be improved by hand as necessary after creation of defaults.

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
import re

def main():
    '''
    Create a json TTS audio file list template with default entries from files in an existing TTS 
    directory, or update an existing template file with new entries from new files.

    Returns:
        (int): 0 on success, 1 on error
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", help="the input directory to crawl", default=os.getcwd())
    parser.add_argument("-f", "--file", help="the name of the output template json file", default="template.json")
    args: argparse.Namespace = parser.parse_args()

    if not os.path.exists(args.directory):
        print(f"Error: directory '{args.directory}' does not exist.")
        return 1

    template: list[dict[str, str]] = []
    file_exists: bool = os.path.isfile(args.file)
    if file_exists:
        try:
            with open(args.file, encoding="utf-8", ) as f:
                template = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"{type(e)}: {e}")
            return 1

    created_count: int = 0
    skipped_count: int = 0
    # Create template data structure from existing directory structure.
    # os.walk does not guarantee order, but Windows seems to return files in order, 
    # while Linux does not, if order matters to you
    for root, _, files in os.walk(args.directory, topdown=False):
        for filename in files:
            # skip non-.mp3 files
            if not filename.endswith(".mp3"):
                continue
            # skip files in voicelines dir since they're not TTS files
            elif "voicelines" in root:
                continue

            # get path relative to sounds dir, remove leading path separator if present
            entry_path: str = os.path.join(root.split("sounds")[1], filename).removeprefix("/")

            # skip if entry path already exists in template list
            if any(entry["path"] == entry_path for entry in template):
                skipped_count += 1
                continue
            else:
                entry_tts_text: str = filename.removesuffix(".mp3")

                # move 'rare' to front of text if it ends with 'rare'
                if entry_tts_text.endswith(" rare"):
                    entry_tts_text = "rare " + entry_tts_text.removesuffix(" rare")
                # move 'magic' to front of text if it ends with 'magic'
                if entry_tts_text.endswith(" magic"):
                    entry_tts_text = "magic " + entry_tts_text.removesuffix(" magic")
                # remove redundant currency prefixes and suffixes such as "orb of " or " orb"
                if "currency/" in entry_path:
                    if entry_tts_text.startswith("orb of "):
                        entry_tts_text = entry_tts_text.removeprefix("orb of ")
                    elif " orb" in entry_tts_text:
                        entry_tts_text = entry_tts_text.replace(" orb", "")
                    elif entry_tts_text.startswith("scroll of "):
                        entry_tts_text = entry_tts_text.removeprefix("scroll of ")
                    elif entry_tts_text.startswith("blacksmiths whetstone"):
                        entry_tts_text = entry_tts_text.removeprefix("blacksmiths ")
                    elif entry_tts_text.startswith("armourers scrap"):
                        entry_tts_text = entry_tts_text.replace(" scrap", "")
                # some models are bad at pronouncing letters, so spell link letters phonetically
                if "links/" in entry_path:
                    matches: list = re.findall(r"\d[bgrw]", entry_tts_text)
                    for match in matches:
                        if "b" in match:
                            entry_tts_text = entry_tts_text.replace(match, f"{match[0]} bee ")
                        elif "g" in match:
                            entry_tts_text = entry_tts_text.replace(match, f"{match[0]} jee ")
                        elif "r" in match:
                            entry_tts_text = entry_tts_text.replace(match, f"{match[0]} arr ")
                        elif "w" in match:
                            entry_tts_text = entry_tts_text.replace(match, f"{match[0]} white")
                    entry_tts_text = entry_tts_text.replace("  ", " ") # charged per char, remove double spaces

                entry_ssml_text: str = ""
                # if tts text is multiple words or is at least 10 characters, set fast rate prosody ssml
                if " " in entry_tts_text or len(entry_tts_text) >= 10:
                    entry_ssml_text = "<prosody rate='fast'>" + entry_tts_text + "</prosody>"
                # literal pronunciation if text contains '1h' or '2h' (otherwise advanced TTS reads "hour")
                if "1h" in entry_ssml_text:
                    entry_ssml_text = entry_ssml_text.replace("1h", "<say-as interpret-as='characters'>1h</say-as>")
                if "2h" in entry_ssml_text:
                    entry_ssml_text = entry_ssml_text.replace("2h", "<say-as interpret-as='characters'>2h</say-as>")

                template.insert(created_count+skipped_count+1, {"path": entry_path, "tts_text": entry_tts_text, "ssml_text": entry_ssml_text})
                created_count += 1
                if created_count > 1:
                    print("\033[1A", end="\x1b[2K")
                print(f"Created entry {created_count}: {template[created_count+skipped_count-1]}", flush=True)

    # create json string from template data structure
    template_json: str = json.dumps(template, indent=4)

    # output json to file
    try:
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(template_json)
    except IOError as e:
        print(f"{type(e)}: {e}")
        return 1

    if file_exists:
        print(f"Updated existing file '{args.file}'. {created_count} new entries created, "
              f"{skipped_count} existing entries skipped.")
    else:
        print(f"Successfully created template file '{args.file}' with {created_count} entries.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
