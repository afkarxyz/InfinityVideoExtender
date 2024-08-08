@echo off
setlocal enabledelayedexpansion
title Video Extender - Extend Your Video Duration!
:: Set path to ffmpeg executables
set "FFMPEG_PATH=%~dp0bin"
set "PATH=%FFMPEG_PATH%;%PATH%"
:start
cls
echo ============================================
echo Video Extender - Extend Your Video Duration!
echo ============================================
echo.
:: List and count video files
set /a count=0
for %%i in (*.mp4 *.avi *.mkv *.mov) do (
    set /a count+=1
    echo !count!. %%i
)
:: Check if any video files are found
if %count% == 0 (
    echo No video files found in this directory.
    echo.
    pause
    exit /b
)
echo.
:: Get user input for file selection
set /p choice=Choose the number of the video file to extend (1-%count%):
:: Validate user input
set /a choice_num=count
if %choice% gtr %choice_num% (
    echo Invalid choice.
    pause
    goto :start
)
:: Find the selected file
set /a file_num=0
for %%i in (*.mp4 *.avi *.mkv *.mov) do (
    set /a file_num+=1
    if !file_num! == %choice% (
        set "input_file=%%i"
        goto :found
    )
)
:found
echo Selected file: %input_file%
:: Get video duration
for /f "tokens=*" %%a in ('ffprobe -v error -show_entries format^=duration -of default^=noprint_wrappers^=1:nokey^=1 "%input_file%"') do (
    set "duration_float=%%a"
)
set /a "duration=%duration_float%"
:: Convert duration to minutes and seconds
set /a "duration_minutes=duration / 60"
set /a "duration_seconds=duration %% 60"
if %duration% gtr 59 (
    echo Original video duration: %duration_minutes% minutes %duration_seconds% seconds
) else (
    echo Original video duration: %duration% seconds
)
:: Ask for desired duration in hours
set /p desired_hours=Enter the desired duration in hours:
set /a desired_seconds=desired_hours * 3600
:: Calculate number of repetitions needed
set /a repeat=(desired_seconds + duration - 1) / duration
echo Number of repetitions needed: %repeat%
:: Create concat file
set "concatfile=concat.txt"
echo file '%input_file%'>"%concatfile%"
for /l %%i in (1,1,%repeat%) do (
    echo file '%input_file%'>>"%concatfile%"
)
:: Generate output filename
set "output_file=%input_file:~0,-4%_%desired_hours%%input_file:~-4%"
:: Run ffmpeg to extend the video
ffmpeg -f concat -safe 0 -i "%concatfile%" -c copy "%output_file%"
del "%concatfile%"
echo.
echo Video has been successfully extended and saved as %output_file%
echo New video duration: approximately %desired_hours% hours (%desired_seconds% seconds)
echo.
pause
exit /b