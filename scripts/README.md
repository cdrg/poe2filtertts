## Typical workflow:

1. If a `template.json` file for your soundpack does not already exist, create a template.json file from an existing set of soundpack folders and mp3 files with:
	- `poetry run python createttstemplate.py [-d INPUT_DIRECTORY] [-f OUTPUT_FILE]`
2. Modify the template entries that you want to improve by hand, if any.
3. Run `poetry run python ttsfromtemplate_awspolly.py [-f INPUT_FILE] [-d OUTPUT_DIRECTORY] voice`
	- **voice** is a valid AWS Polly voice ID. The default locale for that voice will be used.
	- You must have an AWS account and be logged in using `awscli`.
4. Post-process normalize the generated mp3 files to make them louder, eg using an Audacity macro, since the Polly output volume and game sound file volume are relatively low.