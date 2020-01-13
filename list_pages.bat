@if _%1==_ (
 @set /P API_URL="Input wiki URL in required format"
) else (
 @set API_URL=%1
)
@if not exist .\data (
 @mkdir .\data
)
call poetry run python wiki_tool_python\wikitool.py list-pages --output-file .\data\pages.txt %API_URL%
@pause
