# wikit_tool_python

Script to perform various tasks with from sites (wikiprojects) on [MediaWiki](https://www.mediawiki.org/) engine using MediaWiki API.

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
pipenv run python wikitool.py --help
```

## Usage

### Getting help

`--help` Show help message and exit. If this option is used with command, then help message for that specific command will be printed.

### Setting login and password

Some commands require authentication. To tell login and password, use option `--credentials LOGIN:PASSWORD` or set environment variable `MEDIAWIKI_CREDENTIALS` to `LOGIN:PASSWORD`.

### Selecting MediaWiki version

To select MediaWiki version, use option `--mediawiki-version VERSION`. Versions `1.31` and `1.19` are allowed, but `1.19` is not fully supported. Version `1.31` is default.

### MediaWiki API URL

Parameter `API_URL` should be URL of MediaWiki API without `/api.php`, for example https://wow.gamepedia.com or https://absurdopedia.wiki/w.

### Command `list-images`

`python wikitool.py list-images [OPTIONS] API_URL`

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
TODO list-images https://wow.gamepedia.com
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

`python wikitool.py list-pages [OPTIONS] API_URL`

List wikiproject page names of all wikiproject namespaces.

Each page name is written on separate line.

**Note**: deleted pages may be listed in command output (we have not checked for this yet).

#### Command `list-pages`: options

`--output-file FILENAME` Text file to write page names (standard output is used by default)

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

#### Command `list-pages`: example

```sh
python wikitool.py list-pages https://wow.gamepedia.com
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

### Command `list-namespace-pages`

`python wikitool.py list-namespace-pages [OPTIONS] API_URL NAMESPACE`

List wikiproject page names of namespace (`NAMESPACE` should be integer ID of namespace).

Each page name is written on separate line.

**Note**: deleted pages may be listed in command output (we have not checked for this yet).

#### Command `list-namespace-pages`: options

`--output-file FILENAME` Text file to write page names (standard output is used by default)

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

#### Command `list-namespace-pages`: example

```sh
python wikitool.py list-namespace-pages https://wow.gamepedia.com 1
```

Output:

*...*

```text
Talk:"Cookie" McWeaksauce
Talk:"Dirty" Larry
Talk:"Dirty" Michael Crowe
Talk:"Let the Fires Come!"/Notes
Talk:"Let the Fires Come!" (Alliance)
Talk:"Let the Fires Come!" (Horde)
Talk:"Red" Jack Findle
Talk:'Tis the Season
Talk:1.11.0 API changes (Iriel)
Talk:1.8.4
Talk:10-day Free Trial
Talk:19 Pound Catfish
Talk:1st Legion
```

*...*

### Command `list-deletedrevs`

`python wikitool.py list-deletedrevs [OPTIONS] OUTPUT_DIRECTORY API_URL`

List delted revisions from wikiproject in JSON format, output may be splitted to many JSON files, files are saved to `OUTPUT_DIRECTORY`.

**Note**: this command requires authentication.

**Note**: files will be named: `entry-N.json`, where `N` is number of file, starting from 0.

#### Command `list-deletedrevs`: options

`--all-namespaces BOOLEAN` Boolean value, `TRUE` to list for all namespaces, `FALSE` for main namespace only.

`--file-entry-num INTEGER` Number of entries per JSON file.

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

### Command `delete-pages`

`python wikitool.py delete-pages [OPTIONS] FILTER_EXPRESSION API_URL`

Delete pages matching regular expression `FILTER_EXPRESSION`.

**Note**: this command requires authentication.

**Note**: this command deletes pages, use it with caution!

**Note**: regular expressions are parsed with module `re` of python standard library. See [re documentation](https://docs.python.org/3.7/library/re.html) for details.

#### Command `delete-pages`: options

`--reason TEXT` Deletion reason.

`--exclude-expression TEXT` Additional expression to exclude pages matching it from deletion.

`--first-page TEXT` First page to delete (start deletion from it).

`--first-page-namespace INTEGER` Namespace of first page to delete.

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

### Command `edit-pages`

`python wikitool.py edit-pages [OPTIONS] FILTER_EXPRESSION NEW_TEXT API_URL`

Edit pages matching regular expression `FILTER_EXPRESSION`, replacing their content with new text `NEW_TEXT`.

**Note**: this command requires authentication.

**Note**: this command edits pages, use it with caution!

**Note**: regular expressions are parsed with module `re` of python standard library. See [re documentation](https://docs.python.org/3.7/library/re.html) for details.

#### Command `edit-pages`: options

`--reason TEXT` Edit reason.

`--exclude-expression TEXT` Additional expression to exclude pages matching it from editing.

`--first-page TEXT` First page to edit (start editing from it).

`--first-page-namespace INTEGER` Namespace of first page to edit.

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

### Command `edit-pages-clone-interwikis`

`python wikitool.py edit-pages-clone-interwikis [OPTIONS] API_URL OLD NEW`

Add interwiki `NEW` to pages that contain interwiki `OLD`, but do not contain interwiki `NEW` yet.

For example, if `NEW` is `en-gb`, and `OLD` is `en`, than:

```text
[[en:Jaina Proudmoore]]
```

will be replaced with:

```text
[[en:Jaina Proudmoore]]
[[en-gb:Jaina Proudmoore]]
```

This command may be used, for example, if your wiki contains another language version, and this version has forked, and you need to add interwikis to fork to pages that already contain old version.

**Note**: this command requires authentication.

**Note**: this command edits pages, use it with caution!

#### Command `edit-pages-clone-interwikis`: options

`--reason TEXT` Edit reason.

`--exclude-expression TEXT` Additional expression to exclude pages matching it from editing.

`--first-page TEXT` First page to edit (start editing from it).

`--first-page-namespace INTEGER` Namespace of first page to edit.

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

### Command `download-images`

`python wikitool.py download-images [OPTIONS] LIST_FILE DOWNLOAD_DIR`

Download images listed in file `LIST_FILE` (file should be in the same format as output of `list-images` command) to directory `DOWNLOAD_DIR`.

Each image is downloaded from URL given in file and saved to file with name given in file without namespace (for example, `File:Ogyglo.png` is saved as `Ogyglo.png`).

**Note**: progress bar is displayed.

**Note**: if image can not be downloaded, warning is printed, but process is not stopped.

#### Command `download-images`: options

No specific options.

#### Command `download-images`: example

```sh
python wikitool.py download-images images.txt wiki_images
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
pipenv run python wikitool.py list-images --output-file ../absrudopedia/image.txt https://absurdopedia.wiki/w
pipenv run python wikitool.py download-images ../absurdopedia/image.txt ../absurdopedia/download
```

## Files

*    `mediawiki.py` contains exceptions and classes to interact with MediaWiki API. Abstract base class is named `MediaWikiAPI`, implementations for specific MediaWiki versions are derived from it.
*    `wikitool.py` contains commands described in this file. To parse them, [Click](https://click.palletsprojects.com) is used.

## Special thanks

*   [MediaWiki](https://www.mediawiki.org/wiki/MediaWiki) developers.
*   [Python](https://www.python.org/) developers.
*   [requests](https://3.python-requests.org/) developers.
*   [Click](https://click.palletsprojects.com) developers.
*   Рыцарь (Knight) aka Riddari aka Тэйтанка-птекила (Teitanka-ptekila).
*   Other guys from Absurdopedia, russian version of Uncyclopedia (https://absurdopedia.wiki and https://absurdopedia.net)
*   Other cool guys.
