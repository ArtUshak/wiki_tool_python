@if _%1==_ (
 @set /P API_URL="Input wiki URL in required format"
) else (
 @set API_URL=%1
)
@if not exists .\data\download (
 @mkdir .\data\download
)
call poetry run python wiki_tool_python\wikitool.py list-images --output-file .\data\images.txt %API_URL%
call poetry run python wiki_tool_python\wikitool.py download-images .\data\images.txt .\data\download
@pause
