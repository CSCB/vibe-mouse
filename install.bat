@echo off
setlocal EnableDelayedExpansion
title Vibe Mouse Installer
color 0B
chcp 65001 >nul 2>&1

echo ============================================
echo   Vibe Mouse - One-Click Installer
echo ============================================
echo.

set "PYTHON_CMD="

:: ==========================================================================
:: Step 1: Find Python 3.9+ with venv support
::   PREFERRED: 3.10-3.12 (all deps have pre-built wheels)
::   ACCEPTABLE: 3.9, 3.13+ (some deps may need compilation)
:: ==========================================================================
echo [Step 1/6] Looking for Python 3.9+ (with venv)...

:: === Helper: test a Python for version >= 3.9 AND venv ===
:: Sets FOUND_CMD and FOUND_VER if valid, returns errorlevel 0
goto :DetectPython

:CheckPython
set "CANDIDATE=%~1"
if "!CANDIDATE!"=="" exit /b 1

:: Check if it runs
"!CANDIDATE!" --version >nul 2>&1 || exit /b 1

:: Check version >= 3.9
for /f "tokens=2" %%v in ('"!CANDIDATE!" --version 2^>^&1') do set "VER=%%v"
for /f "tokens=1,2 delims=." %%a in ("!VER!") do (
    set "MAJ=%%a" & set "MIN=%%b"
)
if !MAJ! LSS 3 exit /b 1
if !MAJ! EQU 3 if !MIN! LSS 9 exit /b 1

:: Check venv module
"!CANDIDATE!" -c "import venv" >nul 2>&1 || exit /b 1

:: Valid — store it
set "FOUND_CMD=!CANDIDATE!"
set "FOUND_VER=!VER!"
exit /b 0

:: ==========================================================================
:: Detection chain  (recommended versions first)
:: ==========================================================================
:DetectPython

:: --- Phase A: Preferred versions 3.10-3.12 via py launcher ---
for %%v in (3.12 3.11 3.10) do (
    call :CheckPython "py -%%v"
    if not errorlevel 1 (
        set "PYTHON_CMD=!FOUND_CMD!"
        echo          Found: !FOUND_VER!  ^(recommended, via py -%%v^)
        goto :FoundPython
    )
)

:: --- Phase B: Default py -3 (could be 3.13+, acceptable) ---
call :CheckPython "py -3"
if not errorlevel 1 (
    set "PYTHON_CMD=!FOUND_CMD!"
    echo          Found: !FOUND_VER!  ^(via py -3^)
    goto :FoundPython
)

:: --- Phase C: python / python3 in PATH ---
call :CheckPython "python"
if not errorlevel 1 (
    set "PYTHON_CMD=!FOUND_CMD!"
    echo          Found: !FOUND_VER!  ^(via python^)
    goto :FoundPython
)
call :CheckPython "python3"
if not errorlevel 1 (
    set "PYTHON_CMD=!FOUND_CMD!"
    echo          Found: !FOUND_VER!  ^(via python3^)
    goto :FoundPython
)

:: --- Phase D: py --list scan (other versions) ---
for /f "tokens=2" %%v in ('py --list 2^>^&1 ^| findstr /R "3\.[0-9]"') do (
    call :CheckPython "py -%%v"
    if not errorlevel 1 (
        set "PYTHON_CMD=!FOUND_CMD!"
        echo          Found: !FOUND_VER!  ^(via py -%%v^)
        goto :FoundPython
    )
)

:: --- Phase E: Registry search ---
echo          Searching registry...
for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "$r=@(); $paths='HKLM:\Software\Python\PythonCore','HKCU:\Software\Python\PythonCore','HKLM:\Software\Wow6432Node\Python\PythonCore'; foreach($p in $paths){try{$k=Get-ChildItem $p -EA 0; foreach($v in $k){$ip=Get-ItemProperty $v.PSPath -EA 0; $ex=$ip.ExecutablePath; if(!$ex){$ex=$ip.'(Default)'+'\python.exe'}; if(Test-Path $ex){$r+=$ex}}} }catch{}; $r" 2^>nul`) do (
    call :CheckPython "%%p"
    if not errorlevel 1 (
        set "PYTHON_CMD=!FOUND_CMD!"
        echo          Found: !FOUND_VER!  ^(via registry^)
        goto :FoundPython
    )
)

:: --- Phase F: Common paths (recommended first) ---
for %%p in (
    %LOCALAPPDATA%\Programs\Python\Python312\python.exe
    %LOCALAPPDATA%\Programs\Python\Python311\python.exe
    %LOCALAPPDATA%\Programs\Python\Python310\python.exe
    %LOCALAPPDATA%\Programs\Python\Python313\python.exe
    %LOCALAPPDATA%\Programs\Python\Python39\python.exe
    %USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe
    %USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe
    %USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe
    %USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe
    %USERPROFILE%\AppData\Local\Programs\Python\Python39\python.exe
    C:\Python312\python.exe
    C:\Python311\python.exe
    C:\Python310\python.exe
    C:\Python313\python.exe
    C:\Python39\python.exe
    C:\Program Files\Python312\python.exe
    C:\Program Files\Python311\python.exe
    C:\Program Files\Python310\python.exe
    C:\Program Files\Python313\python.exe
    C:\Program Files\Python39\python.exe
) do (
    if exist "%%p" (
        call :CheckPython "%%p"
        if not errorlevel 1 (
            set "PYTHON_CMD=!FOUND_CMD!"
            echo          Found: !FOUND_VER!  ^(common path^)
            goto :FoundPython
        )
    )
)

:: ==========================================================================
:: No Python found -- try auto-install or show instructions
:: ==========================================================================
echo.
echo [ERROR] No Python 3.9+ with venv support found.
echo.

:: Try winget (Windows 10/11 built-in)
winget --version >nul 2>&1
if not errorlevel 1 (
    echo This computer has winget. Let me install Python for you...
    echo.
    echo Running: winget install Python.Python.3.12 --scope user
    echo.
    winget install Python.Python.3.12 --scope user --accept-source-agreements --silent
    if not errorlevel 1 (
        echo.
        echo Python installed! Please re-run install.bat
        echo.
        pause
        exit /b 0
    )
    echo winget install failed, fallback to manual instructions...
    echo.
)

echo Python 3.9+ is required to run Vibe Mouse.
echo.
echo Quick install options:
echo.
echo   Option 1 (Recommended): Download from python.org
echo     https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
echo     IMPORTANT: Check [x] "Add Python to PATH" during installation
echo.
echo   Option 2: Microsoft Store
echo     Search "Python 3.12" in Microsoft Store and install
echo     NOTE: Store version may have venv issues, use Option 1 if problems occur
echo.
echo   Option 3: If you already have Python installed
echo     Make sure it's in your PATH and re-run this installer
echo     Or manually: py -3 -m venv .venv
echo                   .venv\Scripts\activate.bat
echo                   python -m pip install -r requirements.txt
echo.
pause
exit /b 1

:: ==========================================================================
:: Python found -- continue
:: ==========================================================================
:FoundPython

:: Warn if using 3.13+ (some deps lack pre-built wheels)
for /f "tokens=1,2 delims=." %%a in ("%FOUND_VER%") do (
    if %%a EQU 3 if %%b GTR 12 (
        echo.
        echo [WARN] Python %FOUND_VER% detected. Some packages may need compilation.
        echo          If installation fails, install Python 3.10-3.12 for best compatibility.
        echo.
    )
)

echo [Step 2/6] Checking pip...
%PYTHON_CMD% -m pip --version >nul 2>&1 && (
    echo          pip OK
) || (
    echo          pip not found, installing...
    %PYTHON_CMD% -m ensurepip --upgrade >nul 2>&1 && (
        echo          pip installed
    ) || (
        echo [WARN] ensurepip failed, downloading get-pip.py...
        powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'" >nul 2>&1
        if exist get-pip.py (
            %PYTHON_CMD% get-pip.py >nul 2>&1 && (
                del get-pip.py 2>nul
                echo          pip installed
            ) || (
                echo [ERROR] Failed to install pip
                pause & exit /b 1
            )
        ) else (
            echo [ERROR] Cannot download get-pip.py. Check your network.
            pause & exit /b 1
        )
    )
)

echo [Step 3/6] Creating virtual environment...
set "VENV_VER="
if exist ".venv\pyvenv.cfg" (
    for /f "tokens=2 delims==" %%a in ('type .venv\pyvenv.cfg ^| findstr /i "version"') do (
        for /f "tokens=*" %%b in ("%%a") do set "VENV_VER=%%b"
    )
)

if not exist ".venv" (
    %PYTHON_CMD% -m venv .venv >nul 2>&1
    if not exist ".venv\Scripts\activate.bat" (
        echo [ERROR] venv created but activate.bat missing. venv is broken.
        echo          Try running manually: %PYTHON_CMD% -m venv .venv
        pause & exit /b 1
    )
    echo          venv created
) else (
    rem Check if existing venv matches selected Python
    set "SELECTED_VER="
    for /f "tokens=2" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "SELECTED_VER=%%v"

    if "!VENV_VER!"=="!SELECTED_VER!" (
        echo          venv already exists [Python !VENV_VER!], OK
    ) else (
        if "!VENV_VER!"=="" (
            echo          venv exists but config unreadable, recreating...
        ) else (
            echo          venv exists but version mismatch:
            echo            venv:   !VENV_VER!
            echo            target: !SELECTED_VER!
        )
        echo          Deleting old venv...
        rmdir /s /q .venv >nul 2>&1
        if exist ".venv" (
            echo          rmdir failed, trying PowerShell force delete...
            powershell -NoProfile -Command "Remove-Item -Recurse -Force '.venv'" >nul 2>&1
        )
        if exist ".venv" (
            echo [ERROR] Cannot delete .venv folder. It may be in use.
            echo          Close any programs using this folder and retry.
            pause & exit /b 1
        )
        %PYTHON_CMD% -m venv .venv >nul 2>&1
        if not exist ".venv\Scripts\activate.bat" (
            echo [ERROR] venv created but activate.bat missing. venv is broken.
            echo          Try running manually: %PYTHON_CMD% -m venv .venv
            pause & exit /b 1
        )
        echo          venv recreated
    )
)

echo [Step 4/6] Activating virtual environment...
call .venv\Scripts\activate.bat >nul 2>&1 && (
    echo          venv activated
) || (
    echo [ERROR] Failed to activate venv.
    pause & exit /b 1
)

echo [Step 5/6] Upgrading pip...
python -m pip install --upgrade pip -q >nul 2>&1 && (
    echo          pip upgraded
) || (
    echo          pip upgrade skipped (continuing)
)

echo [Step 6/6] Installing core dependencies...
echo          This may take a few minutes...

set "INSTALL_OK=0"

:: --- Attempt 1: Default PyPI ---
if "!INSTALL_OK!"=="0" (
    echo          [1/6] Trying default PyPI...
    python -m pip install -r requirements.txt --timeout 120 --retries 5 >nul 2>&1 && set "INSTALL_OK=1"
)

:: --- Attempt 2: Tsinghua mirror ---
if "!INSTALL_OK!"=="0" (
    echo          [2/6] Trying Tsinghua mirror...
    python -m pip install -r requirements.txt --timeout 120 --retries 5 -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn >nul 2>&1 && set "INSTALL_OK=1"
)

:: --- Attempt 3: Aliyun mirror ---
if "!INSTALL_OK!"=="0" (
    echo          [3/6] Trying Aliyun mirror...
    python -m pip install -r requirements.txt --timeout 120 --retries 5 -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com >nul 2>&1 && set "INSTALL_OK=1"
)

:: --- Attempt 4: USTC mirror ---
if "!INSTALL_OK!"=="0" (
    echo          [4/6] Trying USTC mirror...
    python -m pip install -r requirements.txt --timeout 120 --retries 5 -i https://pypi.mirrors.ustc.edu.cn/simple --trusted-host pypi.mirrors.ustc.edu.cn >nul 2>&1 && set "INSTALL_OK=1"
)

:: --- Attempt 5: Tencent mirror ---
if "!INSTALL_OK!"=="0" (
    echo          [5/6] Trying Tencent mirror...
    python -m pip install -r requirements.txt --timeout 120 --retries 5 -i https://mirrors.cloud.tencent.com/pypi/simple --trusted-host mirrors.cloud.tencent.com >nul 2>&1 && set "INSTALL_OK=1"
)

:: --- Attempt 6: Huawei mirror (show full output for diagnosis) ---
if "!INSTALL_OK!"=="0" (
    echo          [6/6] Trying Huawei mirror ^(showing output for diagnosis^)...
    python -m pip install -r requirements.txt --timeout 120 --retries 5 -i https://mirrors.huaweicloud.com/repository/pypi/simple --trusted-host mirrors.huaweicloud.com && set "INSTALL_OK=1"
)

if "!INSTALL_OK!"=="1" (
    echo.
    echo          Core dependencies installed successfully!
) else (
    echo.
    echo [ERROR] All install attempts failed.
    echo.
    echo See the error output above for the actual cause.
    echo.
    echo Common fixes:
    echo   1. Check your internet:  ping pypi.org
    echo   2. Corporate firewall? Set proxy:
    echo        set HTTP_PROXY=http://your-proxy:port
    echo        set HTTPS_PROXY=http://your-proxy:port
    echo   3. pywin32 build error? Install VC++ Build Tools:
    echo        https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo   4. Try installing one by one:
    echo        .venv\Scripts\activate.bat
    echo        python -m pip install pynput pystray Pillow
    echo        python -m pip install pywin32 psutil
    echo.
    pause & exit /b 1
)

echo.
echo ============================================
echo   Optional Device Dependencies
echo ============================================

set /p opt1="Install gamepad support (pygame)? [y/N]: "
if /i "!opt1!"=="y" (
    echo          Installing pygame...
    call :InstallOptional pygame
)

set /p opt2="Install Bluetooth support (bleak)? [y/N]: "
if /i "!opt2!"=="y" (
    echo          Installing bleak...
    call :InstallOptional bleak
)

set /p opt3="Install serial/IR support (pyserial)? [y/N]: "
if /i "!opt3!"=="y" (
    echo          Installing pyserial...
    call :InstallOptional pyserial
)

set /p opt4="Install voice input support? [y/N]: "
if /i "!opt4!"=="y" (
    echo          Installing SpeechRecognition + pyaudio...
    call :InstallOptional "SpeechRecognition pyaudio"
)

echo.
echo [Generating launch scripts...]
> start.bat (
    echo @echo off
    echo cd /d "%%~dp0"
    echo call .venv\Scripts\activate.bat
    echo python -m core.main %%*
    echo pause
)

> start-gui.bat (
    echo @echo off
    echo cd /d "%%~dp0"
    echo call .venv\Scripts\activate.bat
    echo python -m core.main --gui
    echo pause
)

echo.
set /p shortcut="Create desktop shortcut? [y/N]: "
if /i "!shortcut!"=="y" (
    echo          Creating shortcut...
    powershell -NoProfile -Command "$desktop=[Environment]::GetFolderPath('Desktop'); $ws=New-Object -ComObject WScript.Shell; $sc=$ws.CreateShortcut((Join-Path $desktop 'Vibe Mouse.lnk')); $sc.TargetPath=(Join-Path $pwd 'start-gui.bat'); $sc.WorkingDirectory=$pwd.Path; $sc.IconLocation='shell32.dll,20'; $sc.Save(); Write-Host '          Done'"
)

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Launch:
echo   start.bat       - Tray mode
echo   start-gui.bat   - GUI client mode
echo.
echo Config:
echo   Open config-tool.html in browser
echo.
pause
goto :EOF

:: ==========================================================================
:: Helper: Install optional package with mirror fallback
:: ==========================================================================
:InstallOptional
set "PKG=%~1"
set "OPT_OK=0"

python -m pip install %PKG% -q >nul 2>&1 && set "OPT_OK=1"

if "!OPT_OK!"=="0" (
    echo          Default failed, trying mirror...
    python -m pip install %PKG% -q -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com >nul 2>&1 && set "OPT_OK=1"
)

if "!OPT_OK!"=="1" (
    echo          OK
) else (
    echo          [WARN] %PKG% install failed
)
exit /b 0