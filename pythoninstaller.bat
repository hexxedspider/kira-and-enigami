@echo off

python --version 2>nul | findstr "3.11" >nul
if errorlevel 1 (
    echo Python 3.11 not found, downloading and installing...

    curl -o python-3.11.9.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

    start /wait python-3.11.9.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

    del python-3.11.9.exe
) else (
    echo Python 3.11 detected!
)

python -m pip install --upgrade pip

py -3.11.9 runThisToGetStarted.py