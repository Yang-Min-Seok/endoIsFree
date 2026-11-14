@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "LOG_DIR=%SCRIPT_DIR%logs"
set "LOG_FILE=%LOG_DIR%\nightlyUpdate.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if errorlevel 1 exit /b 1

call :run >> "%LOG_FILE%" 2>&1
exit /b %ERRORLEVEL%

:run
echo [%date% %time%] Update started.
pushd "%SCRIPT_DIR%"
if errorlevel 1 (
    echo Error: could not enter the repository directory.
    exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo Error: this script must be placed in the endoIsFree Git repository.
    goto :failed
)

echo Fetching updates from origin...
git fetch origin
if errorlevel 1 goto :failed

git rev-parse --verify --quiet refs/remotes/origin/main >nul 2>&1
if errorlevel 1 (
    echo Error: origin/main was not found after fetching.
    goto :failed
)

echo Resetting main to origin/main...
git checkout -f -B main origin/main
if errorlevel 1 goto :failed

git reset --hard origin/main
if errorlevel 1 goto :failed

echo Removing untracked, non-ignored files...
git clean -fd
if errorlevel 1 goto :failed

echo Update completed.
echo [%date% %time%] Update finished successfully.
popd
exit /b 0

:failed
echo Error: update failed. Check the Git output above.
echo [%date% %time%] Update failed.
popd
exit /b 1
