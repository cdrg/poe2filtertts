"""
Make .zip files of TTS soundpack directories for uploading with a github release.
"""

import os
import sys
import argparse
import shutil

import json
import ffmpeg

def main():
    '''
    Make .zip files of TTS soundpack directories for uploading with a github release.

    TODO: First, verify all soundpack dirs versus the template file?

    Warning: Existing .zip files with the same name in the output directory will be overwritten.

    Returns:
        (int): 0 on success, 1 on error
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputdir", help="the input directory containing soundpack dirs", 
                        default=os.getcwd())
    parser.add_argument("-o", "--outputdir", help="the output directory to write zips to", 
                        default=os.path.join(os.path.expanduser("~"), "ttszips"))
    parser.add_argument("-f", "--file", help="the name of the input json template file",
                        default="template.json")
    args: argparse.Namespace = parser.parse_args()

    if not os.path.exists(args.inputdir):
        print(f"Error: input directory '{args.inputdir}' does not exist.")
        return 1
    
    if not os.path.exists(args.outputdir):
        os.makedirs(args.outputdir, mode=0o755, exist_ok=True)
    
    with open(args.file, encoding="utf-8") as f:
        try:
            template: list[dict[str, str]] = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"{type(e)}: {e}")
            return 1

    soundpackdirs: list[str] = [name for name in os.listdir(args.inputdir) 
                                if os.path.isdir(os.path.join(args.inputdir, name)) 
                                and os.path.isdir(os.path.join(args.inputdir, name, "sounds"))]
    
    # Check if all files in the template exist in each soundpack directory
    missing_file: bool = False
    for soundpackdir in soundpackdirs:
        for item in template:
            file_partialpath: str = item["path"]
            file_fullpath: str = os.path.join(args.inputdir, soundpackdir, "sounds", file_partialpath)
            # skip if file already exists
            if not os.path.exists(file_fullpath):
                missing_file = True
                print(f"Warning: TTS file '{file_fullpath}' does not exist in soundpack "
                      f"directory '{soundpackdir}'")

    if missing_file:
        print("TTS files specified in template are missing in one or more soundpack directories.")
        if input("Abort? y/n:").strip().lower() == 'y':
            return 1
    else:
        print("Successful check: All TTS files specified in template file exist in all soundpack directories.")

    # Check if any .mp3 files in each soundpack directory do not exist in the template
    extra_file: bool = False
    for soundpackdir in soundpackdirs:
        soundpackdir_path: str = os.path.join(args.inputdir, soundpackdir)
        for root, _, files in os.walk(soundpackdir_path, topdown=False):
            for filename in files:
                # skip non-.mp3 files
                if not filename.endswith(".mp3"):
                    continue
                # skip files in voicelines dir since they're not TTS files
                elif "voicelines" in root:
                    continue
                # skip quest_item.mp3 since it's not a TTS file
                elif filename == "quest item.mp3":
                    continue

                # get path relative to sounds dir, remove leading path separator if present
                entry_path: str = os.path.join(root.split("sounds")[1], filename).removeprefix("/")

                # skip if entry path already exists in template list
                if not any(entry["path"] == entry_path for entry in template):
                    extra_file = True
                    print(f"Warning: File '{os.path.join(root,filename)}' does not exist in template file.")

    if extra_file:
        print("One or more .mp3 files in a soundpack directory do not exist in template file.")
        if input("Abort? y/n:").strip().lower() == 'y':
            return 1
    else:
        print("Successful check: All .mp3 files in soundpack directories exist in template file.")

    # Generate release files
    for soundpackdir in soundpackdirs:
        soundpackdir_path: str = os.path.join(args.inputdir, soundpackdir)
       
        zip_path: str = os.path.join(args.outputdir, soundpackdir)

        # Make a zip file of the soundpack directory
        shutil.make_archive(base_name=zip_path, format='zip', root_dir=soundpackdir_path)

        # Make a preview audio file of the soundpack.
        # Github README.md only supports video embeds, so put the audio in a video container.
        preview_input_path: str = os.path.join(soundpackdir_path, "sounds/currency/chaos orb.mp3")
        preview_output_path: str = os.path.join(args.outputdir, soundpackdir + ".mp4")
        ffmpeg.input(preview_input_path).output(filename=preview_output_path).run(
                    quiet=True, overwrite_output=True)

        print(f"Created zip '{zip_path}'.zip and preview '{preview_output_path}' from soundpack "
              f"dir '{soundpackdir_path}'")
if __name__ == "__main__":
    sys.exit(main())