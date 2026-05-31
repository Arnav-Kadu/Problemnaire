@echo off
echo Installing dependencies...
pip install -e . --quiet
pip install pyinstaller --quiet

echo.
echo Building problemnaire.exe...
pyinstaller ^
  --onefile ^
  --name problemnaire ^
  --collect-all problemnaire ^
  --hidden-import anthropic ^
  --hidden-import httpx ^
  --hidden-import requests ^
  --hidden-import rich ^
  --hidden-import typer ^
  problemnaire\cli.py

echo.
if exist dist\problemnaire.exe (
    echo Build successful!
    echo Executable: dist\problemnaire.exe
    echo.
    echo Distribute the dist\problemnaire.exe file.
    echo Users run: problemnaire setup   ^(first time^)
    echo           problemnaire analyze  ^(each session^)
    echo           problemnaire progress ^(view history^)
) else (
    echo Build failed. Check errors above.
)
