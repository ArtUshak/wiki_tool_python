# wiki_tool_python

Script to perform various tasks with websites (wikiprojects) on [MediaWiki](https://www.mediawiki.org/) engine using MediaWiki API.

## Installation

Install Python 3.8 or higher, install [poetry](https://python-poetry.org/docs/), run `poetry install --no-dev`.

Then you can just run `poetry run COMMAND` to run specific commands under python virtual environment created by poetry.

Or you can enter poetry shell (by running `poetry shell`) and then type script commands.

### Installation example

Assuming Python 3.8 or higher and poetry are installed.

Initialize and update virtual environment (assuming you are in the folder with this README file):

```sh
poetry install --no-dev
```

Run script:

```sh
poetry run python wiki_tool_python/wikitool.py --help
```

### Windows installation example

Assuming Python 3.8 or higher is installed.

Install poetry (in Windows PowerShell):

```ps1
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -UseBasicParsing).Content | python
```

To install or update libraries, run batch file `update.bat`.

To run script to download images, run batch file `download_images.bat` and input URL, or run batch file with URL as first param, for example: `download_images.bat https://absurdopedia.wiki/w`.

To run script to upload images, run batch file `upload_images.bat` and input your username, password and URL, or run batch file with URL as first param and type your username and password, for example: `upload_images.bat https://absurdopedia.wiki/w` and type username and password.

To run script to get page list, run batch file `list_pages.bat` and input URL, or run batch file with URL as first param, for example: `list_pages.bat https://absurdopedia.wiki/w`.

## Usage

### Getting help

`--help` Show help message and exit. If this option is used with command, then help message for that specific command will be printed.

### Setting login and password

Some commands require authentication. To tell login and password, use option `--credentials LOGIN:PASSWORD` or set environment variable `MEDIAWIKI_CREDENTIALS` to `LOGIN:PASSWORD`.

## Throttling requests

To set interval between requests in seconds, use option `--requests-interval SECONDS`.

### Selecting MediaWiki version

To select MediaWiki version, use option `--mediawiki-version VERSION`. Versions `1.31` and `1.19` are allowed, but `1.19` is not fully supported. Version `1.31` is default.

## Overwriting User-Agent

To set `User-Agent` header, use option `--user-agent STRING`. User-agent is set to `WikiToolPython` by default.

### Force login

To log in if it is not mandatory for API method, use option `--login`.

### MediaWiki API URL

Parameter `API_URL` should be URL of MediaWiki API without `/api.php`, for example [https://wow.gamepedia.com](https://wow.gamepedia.com) or [https://absurdopedia.wiki/w](https://absurdopedia.wiki/w).

### Command `list-images`

`python wiki_tool_python/wikitool.py list-images [OPTIONS] API_URL`

List wikiproject images (titles and URLs).

For each image four lines are printed:

1.   Word `FILE2`.
2.   Image name on wikiproject (including namespace, for example `File:Ogyglo.png`).
3.   Image URL on wikiproject.
4.   Processed file name to save image.

The same format is used by `download-images` command.

**Note**: deleted images may be listed in command output.

**Note**: in earlier versions output format was different.

#### Command `list-images`: options

`--output-file FILENAME` Text file to write image list (standard output is used by default)

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

`--confine-encoding TEXT` Encoding to confine file name to (drop characters outside that encoding)

#### Command `list-images`: example

```sh
python wiki_tool_python/wikitool.py list-images https://wow.gamepedia.com
```

Output:

*...*

```text
FILE2
Achievement guild forgreatjusticerank2.png
https://gamepedia.cursecdn.com/wowpedia/d/d6/Achievement_guild_forgreatjusticerank2.png
02986-Achievement guild forgreatjusticerank2.png
```

*...*

### Command `list-category-images`

`python wiki_tool_python/wikitool.py list-category-images [OPTIONS] API_URL CATEGORY`

List wikiproject images (titles and URLs) from specific category in the same format as `list-images`.

#### Command `list-category-images`: options

`--output-file FILENAME` Text file to write image list (standard output is used by default)

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

`--api-image-ids-limit INTEGER` Maximum number of image IDs per API request (default value is 50).

`--confine-encoding TEXT` Encoding to confine file name to (drop characters outside that encoding)

#### Command `list-category-images`: example

```sh
python wiki_tool_python/wikitool.py list-category-images https://wow.gamepedia.com "Category:Images with watermarks"
```

Output:

*...*

```text
FILE2
Quartermaster Alcorn - Beta.jpg
https://gamepedia.cursecdn.com/wowpedia/2/2a/Quartermaster_Alcorn_-_Beta.jpg
00897-Quartermaster Alcorn - Beta.jpg
```

*...*

### Command `list-pages`

`python wiki_tool_python/wikitool.py list-pages [OPTIONS] API_URL`

List wikiproject page names of all wikiproject namespaces.

Each page name is written on separate line.

**Note**: deleted pages may be listed in command output (we have not checked for this yet).

#### Command `list-pages`: options

`--output-file FILENAME` Text file to write page names (standard output is used by default)

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

#### Command `list-pages`: example

```sh
python wiki_tool_python/wikitool.py list-pages https://wow.gamepedia.com
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

`python wiki_tool_python/wikitool.py list-namespace-pages [OPTIONS] API_URL NAMESPACE`

List wikiproject page names of namespace (`NAMESPACE` should be integer ID of namespace).

Each page name is written on separate line.

**Note**: deleted pages may be listed in command output (we have not checked for this yet).

#### Command `list-namespace-pages`: options

`--output-file FILENAME` Text file to write page names (standard output is used by default)

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

#### Command `list-namespace-pages`: example

```sh
python wiki_tool_python/wikitool.py list-namespace-pages https://wow.gamepedia.com 1
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

`python wiki_tool_python/wikitool.py list-deletedrevs [OPTIONS] OUTPUT_DIRECTORY API_URL`

List deleted revisions from wikiproject in JSON format, output may be splitted to many JSON files, files are saved to `OUTPUT_DIRECTORY`.

**Note**: this command requires authentication.

**Note**: files will be named: `entry-N.json`, where `N` is number of file, starting from 0.

#### Command `list-deletedrevs`: options

`--all-namespaces BOOLEAN` Boolean value, `TRUE` to list for all namespaces, `FALSE` for main namespace only.

`--file-entry-num INTEGER` Number of entries per JSON file.

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

### Command `delete-pages`

`python wiki_tool_python/wikitool.py delete-pages [OPTIONS] FILTER_EXPRESSION API_URL`

Delete pages matching regular expression `FILTER_EXPRESSION`.

**Note**: this command requires authentication.

**Note**: this command deletes pages, use it with caution!

**Note**: regular expressions are parsed with module `re` of python standard library. See [re documentation](https://docs.python.org/3.8/library/re.html) for details.

#### Command `delete-pages`: options

`--reason TEXT` Deletion reason.

`--exclude-expression TEXT` Additional expression to exclude pages matching it from deletion.

`--first-page TEXT` First page to delete (start deletion from it).

`--first-page-namespace INTEGER` Namespace of first page to delete.

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

`--namespace INTEGER` Namespace to search pages for deletion (this option can be used multiple times to add multiple namespaces).

### Command `edit-pages`

`python wiki_tool_python/wikitool.py edit-pages [OPTIONS] FILTER_EXPRESSION NEW_TEXT API_URL`

Edit pages matching regular expression `FILTER_EXPRESSION`, replacing their content with new text `NEW_TEXT`.

**Note**: this command requires authentication.

**Note**: this command edits pages, use it with caution!

**Note**: regular expressions are parsed with module `re` of python standard library. See [re documentation](https://docs.python.org/3.8/library/re.html) for details.

#### Command `edit-pages`: options

`--reason TEXT` Edit reason.

`--exclude-expression TEXT` Additional expression to exclude pages matching it from editing.

`--first-page TEXT` First page to edit (start editing from it).

`--first-page-namespace INTEGER` Namespace of first page to edit.

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

`--namespace INTEGER` Namespace to search pages for deletion (this option can be used multiple times to add multiple namespaces).

### Command `edit-pages-clone-interwikis`

`python wiki_tool_python/wikitool.py edit-pages-clone-interwikis [OPTIONS] API_URL OLD NEW`

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

### Command `replace-links`

`python wiki_tool_python/wikitool.py replace-links [OPTIONS] API_URL OLD NEW`

Replace links to page `OLD` by links to page `NEW`.

For example, if `NEW` is `Wikiproject administrator`, and `OLD` is `Administrator`, than:

```text
Arthur Brahmaguptov was [[administrator]] of [[Encyclopedia Dramatica]].
```

will be replaced with:

```text
Arthur Brahmaguptov was [[Wikiproject administrator|administrator]] of [[Encyclopedia Dramatica]].
```

**Note**: this command requires authentication.

**Note**: this command edits pages, use it with caution!

#### Command `replace-links`: options

`--reason TEXT` Edit reason.

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

#### Command: `replace-links`: example

```sh
python ./wiki_tool_python/wikitool.py replace-links http://wikireality.ru/w Администратор "Администратор википроекта"
```

### Command `download-images`

`python wiki_tool_python/wikitool.py download-images [OPTIONS] LIST_FILE DOWNLOAD_DIR`

Download images listed in file `LIST_FILE` (file should be in the same format as output of `list-images` command) to directory `DOWNLOAD_DIR`.

Each image is downloaded from URL given in file and saved to file with name given in file (for example, `File:Ogyglo.png` may be saved as `00500-Ogyglo.png`).

**Note**: progress bar is displayed.

**Note**: if image can not be downloaded, warning is printed, but process is not stopped.

#### Command `download-images`: options

No specific options.

#### Command `download-images`: example

```sh
python wiki_tool_python/wikitool.py download-images images.txt wiki_images
```

Where `images.txt` is list of images.

Output:

Progress bar is displayed.

Images are downloaded to directory `wiki_images`.

### Command `upload-image`

`python wiki_tool_python/wikitool.py upload-image [OPTIONS] FILE_NAME FILE API_URL`

Upload image `FILE` to wiki with new name `FILE_NAME`.

**Note**: this command requires authentication.

#### Command `upload-image`: options

No specific options.

#### Command `upload-image`: example

```sh
python wiki_tool_python/wikitool.py upload-image NVGogol.png Pic9231i9149i.png https://absurdopedia.wiki/w
```

### Command `upload-images`

`python wiki_tool_python/wikitool.py upload-images [OPTIONS] LIST_FILE DOWNLOAD_DIR API_URL`

Upload images listed in file `LIST_FILE` (file should be in the same format as output of `list-images` command) from directory `DOWNLOAD_DIR` to wiki.

**Note**: this command requires authentication.

**Note**: progress bar is displayed.

**Note**: if image can not be upload, warning is printed, but process is not stopped.

#### Command `upload-images`: options

`--skip-nonexistent/--no-skip-nonexistent` Do not fail on non-existent files, skip them instead

#### Command `upload-images`: example

```sh
python wiki_tool_python/wikitool.py upload-images images.txt wiki_images https://absurdopedia.wiki/w
```

Where `images.txt` is list of images.

Output:

Progress bar is displayed.

### Command `votecount`

`python wiki_tool_python/wikitool.py votecount [OPTIONS] API_URL USER_LIST_FILE`

Get user edit count for users from file `USER_LIST_FILE` and calculate vote power (according to [Wikireality rules](http://wikireality.ru/wiki/%D0%92%D0%B8%D0%BA%D0%B8%D1%80%D0%B5%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D1%81%D1%82%D1%8C:%D0%9A#4.4._.D0.92.D0.B5.D1.81_.D0.B3.D0.BE.D0.BB.D0.BE.D1.81.D0.B0)).

#### Command `votecount`: options

`--api-limit INTEGER` Maximum number of entries per API request (default value is 500).

`--namespacefile FILENAME` JSON file to read namespaces data from.

`--start [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]` Start date for counting edits.

`--end [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]` End date for counting edits.

`--output-format [txt|mediawiki|json]` Output data format (text, MediaWiki table or JSON).

`--redirect-regex-text TEXT` Regular expression to detect redirect creation.

#### Command `votecount`: example

Namespace file `namespaces.json` is:

```json
{
    "edit_weights": {
        "0": 0.04,
        "1": 0.003,
        "4": 0.015,
        "5": 0.003,
        "6": 0.03,
        "7": 0.003,
        "8": 0.015,
        "9": 0.003,
        "10": 0.015,
        "11": 0.003,
        "14": 0.015,
        "15": 0.003
    },
    "page_weights": {
        "0": 0.6
    }
}
```

User list file `../data/votecount/voters.txt` is:

```txt
Arbnos
Arsenal
Cat1987
```

```sh
python wiki_tool_python/wikitool.py --mediawiki-version 1.19 votecount --start 2018-07-12 --end 2018-10-12 --namespacefile ../data/votecount/namespaces.json --output-format txt http://wikireality.ru/w ../data/votecount/voters.txt
```

Output:

```text
Processing user Arbnos...
Processing user Arsenal...
Processing user Cat1987...
User Arbnos
N0: 0
N1: 0
N4: 0
N5: 0
N6: 0
N7: 0
N8: 0
N9: 0
N10: 0
N11: 0
N14: 0
N15: 0
NewPages: 0
VotePower: 0.0

User Arsenal
N0: 20
N1: 0
N4: 9
N5: 0
N6: 0
N7: 0
N8: 0
N9: 0
N10: 2
N11: 0
N14: 0
N15: 0
NewPages: 2
VotePower: 2.165

User Cat1987
N0: 30
N1: 0
N4: 1
N5: 0
N6: 3
N7: 0
N8: 1
N9: 0
N10: 0
N11: 0
N14: 0
N15: 0
NewPages: 0
VotePower: 1.32
```

*...*

### Command `list-directory-pages`

`python wiki_tool_python/wikitool.py list-directory-pages [OPTIONS] INPUT_DIRECTORY OUTPUT_FILE`

Write list of `.txt` file paths in directory to JSON file.

Directories are handled recursively.

#### Command `list-directory-pages`: example

There are files `../data/wiki-pages/Test.txt` and `../data/wiki-pages/Test/Test1.txt`.

```sh
python ./wiki_tool_python/wikitool.py list-directory-pages ../data/wiki-pages/ ../data/wiki-pages-list.json
```

File `../data/wiki-pages-list.json` will contain the following text:

```json
[
    "Test.txt",
    "Test/Test1.txt"
]
```

#### Command `list-directory-pages`: options

No specific options.

### Command `upload-pages`

`python wiki_tool_python/wikitool.py upload-pages [OPTIONS] API_URL INPUT_DIRECTORY LIST_FILE`

Create or overwrite pages from files in input directory listed in list file.

Files with extension are uploaded as pages, page title for file is prefix concatenated with file path (as written in list file) without extension.

**Note**: this command requires authentication.

**Note**: list file format is either JSON list (same as of file generated by `list-directory-pages` command) or JSON dictionary (keys are page pathes, values are page titles).

#### Command `upload-pages`: example 1

There are files `../data/wiki-pages/Test.txt` and `../data/wiki-pages/Test/Test1.txt`.

File `../data/wiki-pages-list.json` contains the following text:

```json
[
    "Test.txt",
    "Test/Test1.txt"
]
```

Command is:

```sh
python ./wiki_tool_python/wikitool.py upload-pages --prefix="User:ArtushakBot/" --summary="Test page upload" https://genepedia.ru ../data/wiki-pages/ ../data/wiki-pages/wiki-pages-list.json
```

The following pages will be created:

*   `User:ArtushakBot/Test` with text from `../data/wiki-pages/Test.txt`
*   `User:ArtushakBot/Test/Test1` with text from `../data/wiki-pages/Test/Test1.txt`

#### Command `upload-pages`: example 2

There are files `../data/wiki-pages/1.txt` and `../data/wiki-pages/2.txt`.

File `../data/wiki-pages-list.json` contains the following text:

```json
{
    "1.txt": "Page 1",
    "2.txt": "Page 2"
}
```

Command is:

```sh
python ./wiki_tool_python/wikitool.py upload-pages --dictionary --prefix="User:ArtushakBot/" --summary="Test page upload" https://genepedia.ru ../data/wiki-pages/ ../data/wiki-pages/wiki-pages-list.json
```

The following pages will be created:

*   `User:ArtushakBot/Page 1` with text from `../data/wiki-pages/Page 1`
*   `User:ArtushakBot/Page 2` with text from `../data/wiki-pages/Page 2`

#### Command `upload-pages`: options

`--dictionary / --no-dictionary` Use dictionary file of pathes and titles instead of file list.

`--extended-dictionary / --no-extended-dictionary` Read dictionary values as dictionaries with `title` and `path` keys.

`--prefix TEXT` Prefix for page titles.

`--summary TEXT` Edit summary.

`--first-page INTEGER` Page number to start with.

`--mode [append|overwrite]` Whether to append text from file to old text on existing pages, or overwrite old text with text from file.

### Command `generate-import-script`

`python wiki_tool_python/wikitool.py list-directory-pages [OPTIONS] LIST_FILE INPUT_DIRECTORY OUTPUT_SCRIPT_FILE LOG_FILE`

Write bash script to import pages from list file using MediaWiki maintenance script `importTextFiles.php` (see [MediaWiki help](https://www.mediawiki.org/wiki/Manual:ImportTextFiles.php)). It can be uploaded to server along with page files and then run to import to them to website to avoid API overhead.

`LIST_FILE` is path to page list file *on local machine*. `INPUT_DIRECTORY` is parent path for page text files *on server*, path should be absolute or relative to script working directory.

`LOG_FILE` is path to output text log file *on server*, path should be absolute or relative to script working directory.

**Note**: server access (for example, SSH) is required for this method of page uploading.

### Command `generate-import-script`: options

`--prefix TEXT` Prefix for page titles.

`--rc / --no-rc` Add `--rc` option to output script.

`--bot / --no-bot` Add `--bot` option to output script.

`--user TEXT` Add -u option to output script.

`--summary TEXT` Add -s option to output script.

`--maintenance-directory TEXT` Directory with `importTextFiles.php` script *on server*, path should be absolute or relative to script working directory.

`--show-progress-bar / --no-show-progress-bar` Add progress bar display to output script

`--first-page INTEGER` First page number to add

### Command `generate-import-script`: example

There are files `../data/wiki-pages/Test.txt` and `../data/wiki-pages/Test/Test1.txt`.

File `../data/wiki-pages-list.json` contains the following text:

```json
[
    "Test.txt",
    "Test/Test1.txt"
]
```

Command is:

```sh
python ./wiki_tool_python/wikitool.py generate-import-script --prefix="User:ArtushakBot/" --summary="Test page upload" --bot --maintenance-directory="/srv/http/mediawiki/w/maintenance" ../data/wiki-pages/wiki-pages-list.json ./data/wiki-pages ../data/importPages.sh ./data/log.txt
```

File `../data/importPages.sh` will contain following text:

```bash
#!/bin/bash

php /srv/http/mediawiki/w/maintenance/importTextFiles.php --rc --bot -s 'Test page upload' --prefix User:ArtushakBot/ data/wiki-pages/Test.txt >> ./data/log.txt 2>&1 
echo -ne '[##########          ]         1 /         2\r'
php /srv/http/mediawiki/w/maintenance/importTextFiles.php --rc --bot -s 'Test page upload' --prefix User:ArtushakBot/Test/ data/wiki-pages/Test/Test1.txt >> ./data/log.txt 2>&1 
echo -ne '[####################]         2 /         2\r'
```

## Main example

```sh
poetry install --no-dev
mkdir ../absurdopedia
mkdir ../absurdopedia/download
poetry run python wiki_tool_python/wikitool.py list-images --output-file ../absurdopedia/image.txt https://absurdopedia.wiki/w
poetry run python wiki_tool_python/wikitool.py download-images ../absurdopedia/image.txt ../absurdopedia/download
```

## Files

*   `mediawiki.py` contains exceptions and classes to interact with MediaWiki API. Abstract base class is named `MediaWikiAPI`, implementations for specific MediaWiki versions are subclassed from it.
*   `wikitool.py` contains commands described in this file. To parse them, [Click](https://click.palletsprojects.com) is used.

## Special thanks

*   [MediaWiki](https://www.mediawiki.org/wiki/MediaWiki) developers.
*   [Python](https://www.python.org/) developers.
*   [Poetry](https://python-poetry.org/) developers.
*   [requests](https://3.python-requests.org/) developers.
*   [Click](https://click.palletsprojects.com) developers.
*   Рыцарь (Knight) aka Riddari aka Тэйтанка-птекила (Teitanka-ptekila).
*   [Wikireality](http://wikireality.ru) users, especially members of Dimetr's Telegram chat.
*   Other folks from Absurdopedia, russian version of Uncyclopedia ([absurdopedia.wiki](https://absurdopedia.wiki/) and [absurdopedia.net](https://absurdopedia.net/))
*   Other cool folks.
