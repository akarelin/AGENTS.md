@echo off
echo === Arxiv Paper Organizer ===
echo.
echo Scanning D:\Downloads recursively...
echo.
python "%~dp0arxiv_organizer.py" --scan "D:\Downloads" --recurse --library "C:\Users\Alex\OneDrive - Karelin\Library"
echo.
echo ---
set /p confirm="Execute? (y/n): "
if /i "%confirm%"=="y" (
    echo.
    echo Executing...
    python "%~dp0arxiv_organizer.py" --execute "D:\Downloads" --recurse --library "C:\Users\Alex\OneDrive - Karelin\Library"
)
echo.
pause