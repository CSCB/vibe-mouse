#requires -Version 5.1
<#
  Vibe Mouse - One-Click Installer (PowerShell)
  Run:  powershell -ExecutionPolicy Bypass -File install.ps1
#>

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-Python {
    param([string]$Cmd)
    try {
        $ver = (& $Cmd --version 2>&1).Trim()
        if ($ver -match 'Python\s+(\d+)\.(\d+)') {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 9)) {
                # Check venv
                $hasVenv = & $Cmd -c "import venv" 2>&1
                if ($LASTEXITCODE -eq 0) {
                    return [PSCustomObject]@{
                        Cmd     = $Cmd
                        Version = "$major.$minor"
                        Path    = $null
                    }
                }
            }
        }
    } catch { }
    return $null
}

function Test-PythonPath {
    param([string]$ExePath)
    if (-not (Test-Path $ExePath)) { return $null }
    return Test-Python -Cmd $ExePath
}

function Find-Python {
    $candidates = @()

    # --- Phase A: Preferred versions 3.10-3.12 via py launcher ---
    foreach ($ver in @('3.12', '3.11', '3.10')) {
        $p = Test-Python -Cmd "py -$ver"
        if ($p) {
            $p.Source = "py -$ver (recommended)"
            $candidates += $p
        }
    }

    # --- Phase B: Default py -3 ---
    $p = Test-Python -Cmd "py -3"
    if ($p) {
        $p.Source = "py -3"
        $candidates += $p
    }

    # --- Phase C: python / python3 in PATH ---
    $p = Test-Python -Cmd "python"
    if ($p) {
        $p.Source = "python"
        $candidates += $p
    }
    $p = Test-Python -Cmd "python3"
    if ($p) {
        $p.Source = "python3"
        $candidates += $p
    }

    # --- Phase D: py --list scan (other versions) ---
    try {
        $list = (& py --list 2>&1) -join "`n"
        $matches = [regex]::Matches($list, '3\.(\d+)')
        foreach ($m in $matches) {
            $minor = [int]$m.Groups[1].Value
            if ($minor -ge 9) {
                $ver = $m.Value
                $p = Test-Python -Cmd "py -$ver"
                if ($p) {
                    $p.Source = "py -$ver"
                    $candidates += $p
                }
            }
        }
    } catch { }

    # --- Phase E: Registry search ---
    $regPaths = @(
        'HKLM:\Software\Python\PythonCore',
        'HKCU:\Software\Python\PythonCore',
        'HKLM:\Software\Wow6432Node\Python\PythonCore'
    )
    foreach ($rp in $regPaths) {
        try {
            $versions = Get-ChildItem -Path $rp -ErrorAction SilentlyContinue | Select-Object -ExpandProperty PSChildName
            foreach ($v in $versions) {
                try {
                    $ip = Get-ItemProperty -Path "$rp\$v\InstallPath" -ErrorAction Stop
                    $exe = $ip.ExecutablePath
                    if (-not $exe) { $exe = Join-Path $ip.'(Default)' 'python.exe' }
                    $p = Test-PythonPath -ExePath $exe
                    if ($p) {
                        $p.Path = $exe
                        $p.Source = "registry"
                        $candidates += $p
                    }
                } catch { }
            }
        } catch { }
    }

    # --- Phase F: Common paths (recommended first) ---
    $commonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python310\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python313\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python39\python.exe",
        'C:\Python312\python.exe',
        'C:\Python311\python.exe',
        'C:\Python310\python.exe',
        'C:\Python313\python.exe',
        'C:\Python39\python.exe',
        'C:\Program Files\Python312\python.exe',
        'C:\Program Files\Python311\python.exe',
        'C:\Program Files\Python310\python.exe',
        'C:\Program Files\Python313\python.exe',
        'C:\Program Files\Python39\python.exe'
    )
    foreach ($cp in $commonPaths) {
        $p = Test-PythonPath -ExePath $cp
        if ($p) {
            $p.Path = $cp
            $p.Source = "common path"
            $candidates += $p
        }
    }

    # Pick best: prefer 3.10-3.12, then highest version
    $preferred = $candidates | Where-Object {
        $parts = $_.Version.Split('.')
        [int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10 -and [int]$parts[1] -le 12
    } | Sort-Object { [version]$_.Version } -Descending | Select-Object -First 1

    if ($preferred) { return $preferred }

    return $candidates | Sort-Object { [version]$_.Version } -Descending | Select-Object -First 1
}

function Install-Dependencies {
    $mirrors = @(
        @{ Url = "https://pypi.tuna.tsinghua.edu.cn/simple"; Host = "pypi.tuna.tsinghua.edu.cn" },
        @{ Url = "https://mirrors.aliyun.com/pypi/simple"; Host = "mirrors.aliyun.com" },
        @{ Url = "https://pypi.mirrors.ustc.edu.cn/simple"; Host = "pypi.mirrors.ustc.edu.cn" },
        @{ Url = "https://mirrors.cloud.tencent.com/pypi/simple"; Host = "mirrors.cloud.tencent.com" },
        @{ Url = "https://mirrors.huaweicloud.com/repository/pypi/simple"; Host = "mirrors.huaweicloud.com" }
    )

    Write-Host "          This may take a few minutes..."

    # Try default PyPI
    Write-Host "          [1/6] Trying default PyPI..." -NoNewline
    $null = python -m pip install -r requirements.txt --timeout 120 --retries 5 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
        return $true
    }
    Write-Host " FAILED" -ForegroundColor Red

    # Try mirrors (suppress output except last)
    $total = $mirrors.Count
    for ($i = 0; $i -lt $total; $i++) {
        $m = $mirrors[$i]
        $attemptNum = $i + 2
        $isLast = ($i -eq $total - 1)

        if ($isLast) {
            Write-Host "          [$attemptNum/6] Trying $($m.Host) (showing output for diagnosis)..."
            python -m pip install -r requirements.txt --timeout 120 --retries 5 -i $m.Url --trusted-host $m.Host
            if ($LASTEXITCODE -eq 0) {
                Write-Host "          Installed via mirror" -ForegroundColor Green
                return $true
            }
        } else {
            Write-Host "          [$attemptNum/6] Trying $($m.Host)..." -NoNewline
            $null = python -m pip install -r requirements.txt --timeout 120 --retries 5 -i $m.Url --trusted-host $m.Host 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host " OK" -ForegroundColor Green
                return $true
            }
            Write-Host " FAILED" -ForegroundColor Red
        }
    }
    return $false
}

# ============================================================================
# Main
# ============================================================================
Write-Header "Vibe Mouse - One-Click Installer"

# --- Step 1: Find Python ---
Write-Host "[Step 1/6] Looking for Python 3.9+ (with venv)..." -NoNewline
$python = Find-Python
if (-not $python) {
    Write-Host " NOT FOUND" -ForegroundColor Red
    Write-Host ""

    # Try winget auto-install
    try {
        $winget = Get-Command winget -ErrorAction Stop
        Write-Host "This computer has winget. Let me install Python for you..." -ForegroundColor Yellow
        Write-Host "Running: winget install Python.Python.3.12 --scope user" -ForegroundColor Yellow
        Write-Host ""
        winget install Python.Python.3.12 --scope user --accept-source-agreements --silent
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "Python installed! Please re-run install.ps1" -ForegroundColor Green
            Read-Host "Press Enter to exit"
            exit 0
        }
    } catch { }

    Write-Host "[ERROR] Python 3.9+ with venv support not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Quick install options:"
    Write-Host ""
    Write-Host "  Option 1 (Recommended): Download from python.org"
    Write-Host "    https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    Write-Host "    IMPORTANT: Check [x] 'Add Python to PATH' during installation"
    Write-Host ""
    Write-Host "  Option 2: Microsoft Store"
    Write-Host "    Search 'Python 3.12' in Microsoft Store and install"
    Write-Host "    NOTE: Store version may have venv issues, use Option 1 if problems occur"
    Write-Host ""
    Write-Host "  Option 3: If you already have Python installed"
    Write-Host "    Make sure it's in your PATH and re-run this installer"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host " OK ($($python.Version) via $($python.Source))" -ForegroundColor Green

# Warn if using 3.13+ (some deps lack pre-built wheels)
$verParts = $python.Version.Split('.')
if ([int]$verParts[0] -eq 3 -and [int]$verParts[1] -gt 12) {
    Write-Host ""
    Write-Host "[WARN] Python $($python.Version) detected. Some packages may need compilation." -ForegroundColor Yellow
    Write-Host "       If installation fails, install Python 3.10-3.12 for best compatibility." -ForegroundColor Yellow
    Write-Host ""
}

# --- Step 2: Check pip ---
Write-Host "[Step 2/6] Checking pip..." -NoNewline
$pythonExe = if ($python.Path) { $python.Path } else { $python.Cmd }
try {
    & $pythonExe -m pip --version >$null 2>&1
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host " installing..." -NoNewline
    try {
        & $pythonExe -m ensurepip --upgrade >$null 2>&1
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " downloading get-pip.py..." -NoNewline
        try {
            Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing
            & $pythonExe get-pip.py >$null 2>&1
            Remove-Item get-pip.py -Force -ErrorAction SilentlyContinue
            Write-Host " OK" -ForegroundColor Green
        } catch {
            Write-Host " FAILED" -ForegroundColor Red
            Write-Host "[ERROR] Cannot install pip. Check your network." -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
}

# --- Step 3: Create venv ---
Write-Host "[Step 3/6] Creating virtual environment..." -NoNewline
if (-not (Test-Path ".venv")) {
    & $pythonExe -m venv .venv >$null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " created" -ForegroundColor Green
    } else {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "[ERROR] Failed to create venv. Try manually: $pythonExe -m venv .venv" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host " already exists" -ForegroundColor Yellow
}

# --- Step 4: Activate venv ---
Write-Host "[Step 4/6] Activating virtual environment..." -NoNewline
$activateScript = ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    . $activateScript
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# --- Step 5: Upgrade pip ---
Write-Host "[Step 5/6] Upgrading pip..." -NoNewline
python -m pip install --upgrade pip -q >$null 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " skipped (continuing)" -ForegroundColor Yellow
}

# --- Step 6: Install dependencies ---
Write-Host "[Step 6/6] Installing core dependencies..."
$ok = Install-Dependencies
if (-not $ok) {
    Write-Host ""
    Write-Host "[ERROR] All install attempts failed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible causes:"
    Write-Host "  1. No internet connection"
    Write-Host "  2. Corporate firewall blocking PyPI"
    Write-Host "  3. pywin32 requires Visual C++ Build Tools"
    Write-Host ""
    Write-Host "Manual fix:"
    Write-Host "  .venv\Scripts\activate.bat"
    Write-Host "  python -m pip install -r requirements.txt"
    Write-Host ""
    Write-Host "If pywin32 fails, install VC++ Build Tools from:"
    Write-Host "  https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    Read-Host "Press Enter to exit"
    exit 1
}

# --- Optional dependencies ---
Write-Header "Optional Device Dependencies"

function Install-Optional {
    param([string]$Package)
    Write-Host "          Installing $Package..." -NoNewline
    $null = python -m pip install $Package -q 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
        return
    }
    Write-Host " mirror..." -NoNewline
    $null = python -m pip install $Package -q -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Host " OK" -ForegroundColor Green }
    else { Write-Host " FAILED" -ForegroundColor Yellow }
}

$opt1 = Read-Host "Install gamepad support (pygame)? [y/N]"
if ($opt1 -eq 'y' -or $opt1 -eq 'Y') { Install-Optional "pygame" }

$opt2 = Read-Host "Install Bluetooth support (bleak)? [y/N]"
if ($opt2 -eq 'y' -or $opt2 -eq 'Y') { Install-Optional "bleak" }

$opt3 = Read-Host "Install serial/IR support (pyserial)? [y/N]"
if ($opt3 -eq 'y' -or $opt3 -eq 'Y') { Install-Optional "pyserial" }

$opt4 = Read-Host "Install voice input support? [y/N]"
if ($opt4 -eq 'y' -or $opt4 -eq 'Y') { Install-Optional "SpeechRecognition pyaudio" }

# --- Launch scripts ---
Write-Host ""
Write-Host "[Generating launch scripts...]"
@'
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m core.main %*
pause
'@ | Set-Content -Path "start.bat" -Encoding ASCII

@'
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m core.main --gui
pause
'@ | Set-Content -Path "start-gui.bat" -Encoding ASCII

# --- Desktop shortcut ---
Write-Host ""
$shortcut = Read-Host "Create desktop shortcut? [y/N]"
if ($shortcut -eq 'y' -or $shortcut -eq 'Y') {
    Write-Host "          Creating shortcut..." -NoNewline
    try {
        $desktop = [Environment]::GetFolderPath('Desktop')
        $wsh = New-Object -ComObject WScript.Shell
        $lnk = $wsh.CreateShortcut("$desktop\Vibe Mouse.lnk")
        $lnk.TargetPath = "$PWD\start-gui.bat"
        $lnk.WorkingDirectory = "$PWD"
        $lnk.Save()
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " skipped" -ForegroundColor Yellow
    }
}

# --- Done ---
Write-Header "Installation Complete!"
Write-Host "Launch:"
Write-Host "  start.bat       - Tray mode"
Write-Host "  start-gui.bat   - GUI client mode"
Write-Host ""
Write-Host "Config:"
Write-Host "  Open config-tool.html in browser"
Write-Host ""
Read-Host "Press Enter to exit"