@echo off
chcp 65001 >nul
set PORT=13100

echo ========================================
echo   关闭 AI 自动装修助手测试服务器
echo ========================================
echo.

echo [信息] 正在查找占用端口 %PORT% 的进程...
echo.

REM 查找占用端口的进程
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% "') do (
    set PID=%%a
    goto :found
)

echo [警告] 未找到占用端口 %PORT% 的进程
echo.
pause
exit /b 0

:found
echo [信息] 找到进程 PID: %PID%
echo [信息] 正在终止进程...
echo.

REM 终止进程
taskkill /F /PID %PID% >nul 2>&1

if %errorlevel% equ 0 (
    echo [成功] 服务器已关闭 (PID: %PID%)
) else (
    echo [错误] 无法关闭进程，请手动关闭命令行窗口
)

echo.
echo ========================================
pause
