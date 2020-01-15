@set /P MEDIAWIKI_USER="Input your wiki user name"
@set /P MEDIAWIKI_PASSWORD="Input your wiki user password"
@set MEDIAWIKI_CREDENTIALS=%MEDIAWIKI_USER%:%MEDIAWIKI_PASSWORD%
@if _%1==_ (
 @set /P API_URL="Input wiki URL in required format"
) else (
 @set API_URL=%1
)
@if not exist .\data\download (
 @mkdir .\data\download
)
call poetry run python wiki_tool_python\wikitool.py upload-images .\data\images.txt .\data\download %API_URL%
@pause
