# Wiki-Export

Script for exporting data from sites (wikiprojects) on [MediaWiki](https://www.mediawiki.org/) engine using MediaWiki API.

## Installation

Install Python 3.7, install `pipenv`, run `pipenv update`.

Then you can just run `pipenv run COMMAND` to run specific commands under pipenv.

Or you can enter pipenv shell (by running `pipenv shell`) and then type script commands.

### Example

Assuming python 3.7 is installed and you.

Installing `pipenv` (if you do not have it) via `pip` (there are also some other ways of pipenv installation):

```sh
pip3 install --user pipenv
```

Initialising and updating virtual environment (assuming you are in the folder with this script):

```sh
pipenv update
```

Running script:

```sh
pipenv run python wikiexport.py --help
```

## Usage

### Getting help

`--help` Show help message and exit

### MediaWiki API URL

`API_URL` should be URL of MediaWiki API, for example https://absurdopedia.fandom.com/api.php.

### Command `list-images`

`python wikiexport.py list-images [OPTIONS] API_URL`

List wikiproject images (titles and URLs).

For each image three lines are printed:

1. Word `FILE`.
2. Image name on wikiproject (including namespace, for example `File:Ogyglo.png`).
3. Image URL on wikiproject.

The same format is used by `download-images` command.

**Note**: deleted images may be listed in command output.

#### Command `list-images`: options

`--output-file FILENAME` Text file to write image list (standard output is used by default)

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

#### Command `list-images`: example

```sh
TODO list-images https://wow.gamepedia.com/api.php
```

Output:

*...*

```text
FILE
File:(2)TheTwoRivers.jpg
https://gamepedia.cursecdn.com/wowpedia/1/1c/%282%29TheTwoRivers.jpg
```

*...*

### Command `list-pages`

`python wikiexport.py list-pages [OPTIONS] API_URL`

List wikiproject page names of all wikiproject namespaces.

Each page name is written on separate line.

**Note**: deleted pages may be listed in command output (we have not checked for this yet).

#### Command `list-pages`: options

`--output-file FILENAME` Text file to write page names (standard output is used by default)

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

#### Command `list-pages`: example

```sh
python wikiexport.py list-pages https://wow.gamepedia.com/api.php
```

Output:

*...*

```text
Talk:Alchemist (Warcraft III)
Talk:Alchemist Finklestein
Talk:Alchemist Pestlezugg
Talk:Alchemist Stone
Talk:Alchemy
Talk:Alchemy Lab
Talk:Alchemy proficiencies
Talk:Alchemy recipes
Talk:Alchemy recipes/Grand Master
Talk:Alchemy trainers)
```

*...*

### Command `download-images`

`python wikiexport.py download-images [OPTIONS] LIST_FILE DOWNLOAD_DIR`

Download images listed in file `LIST_FILE` (file should be in the same format as output of `list-images` command) to directory `DOWNLOAD_DIR`.

Each image is downloaded from URL given in file and saved to file with name given in file without namespace (for example, `File:Ogyglo.png` is saved as `Ogyglo.png`).

**Note**: progress bar is displayed.

**Note**: if image can not be downloaded, warning is printed, but process is not stopped.

#### Command `download-images`: options

No specific options.

#### Command `download-images`: example

```sh
python wikiexport.py download-images images.txt wiki_images
```

Where `images.txt` is list of images.

Output:

Progress bar is displayed.

Images are downloaded to directory `wiki_images`.

## Example

```
pip3.7 install --user pipenv
pipenv update
mkdir ../absurdopedia
mkdir ../absurdopedia/download
pipenv run python wikiexport.py list-images --output-file ../absrudopedia/image.txt https://absurdopedia.fandom.com/api.php
pipenv run python wikiexport.py download-images ../absurdopedia/image.txt ../absurdopedia/download
```

## Special thanks

*   [MediaWiki](https://www.mediawiki.org/wiki/MediaWiki) developers.
*   Рыцарь (Knight) aka Riddari.
*   Other cool guys.
