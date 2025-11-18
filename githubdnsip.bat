@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ================================================================
REM "GitHub 相关域名 DNS 查询脚本 过滤解析器自身IP + 全局去重"
REM ------------------------------------------------
REM "用法"
REM   githubdnsip.bat
REM   githubdnsip.bat <dns>
REM   githubdnsip.bat <dns> <ipver>
REM "参数"
REM   "<dns>    递归DNS服务器  默认 208.67.222.222"
REM   "<ipver>  4=仅A, 6=仅AAAA, 46 或空=两者"
REM "去重范围 全局  所有域名 + A/AAAA 去重"
REM "若需每个域名单独去重，可在域名循环里重置 SEEN_IPS= "
REM ================================================================

set "DNS=%~1"
if "%DNS%"=="" set "DNS=208.67.222.222"
set "IPVER=%~2"
if "%IPVER%"=="" set "IPVER=4"

REM "全局已出现 IP 列表 前导空格便于精确匹配"
set "SEEN_IPS= "

REM "待查询域名  github.githubassets.com user-images.githubusercontent.com avatars.githubusercontent.com objects.githubusercontent.com  api.github.com  raw.githubusercontent.com"
set "DOMAINS=github.com github.global.ssl.fastly.net codeload.github.com"

echo Using resolver: %DNS%
echo Query types: %IPVER%
echo.

for %%D in (%DOMAINS%) do (
  echo ===== %%D =====
  echo.
  REM "如果想按域名单独去重，在此处加  set \"SEEN_IPS= \""

  echo %IPVER% | findstr "4" >nul && call :DoLookup %%D A
  echo %IPVER% | findstr "6" >nul && call :DoLookup %%D AAAA

  echo.
)

goto :EOF

:DoLookup
REM "%1 = domain, %2 = type A / AAAA"
nslookup -type=%2 %1 %DNS% > "%TEMP%\__gh_ns.tmp" 2>nul
if errorlevel 1 (
  echo [%2] %1 : lookup failed
  del /q "%TEMP%\__gh_ns.tmp" >nul 2>nul
  goto :EOF
)

set "IN_ADDR_BLOCK=0"
for /f "usebackq delims=" %%L in ("%TEMP%\__gh_ns.tmp") do (
  set "LINE=%%L"

  if /I "!LINE:~0,7!"=="Server:" (
    REM skip
  ) else (
    if /I "!LINE:~0,5!"=="Name:" (
      echo [%2] !LINE!
    ) else (
      REM "处理 Address 与 Addresses"
      echo(!LINE!| findstr /R /B /I "Address:  *" >nul && (
        call :PrintAddress %2 "!LINE!"
      )
      echo(!LINE!| findstr /R /B /I "Addresses:  *" >nul && (
        call :PrintAddress %2 "!LINE!"
        set "IN_ADDR_BLOCK=1"
      )

      REM "处理 Addresses 后续续行 前导空格 + IP"
      if !IN_ADDR_BLOCK! EQU 1 (
        echo(!LINE!| findstr /R "^[ ][ ]*[0-9A-Fa-f][0-9A-Fa-f:.]*$" >nul
        if errorlevel 1 (
          set "IN_ADDR_BLOCK=0"
        ) else (
          call :PrintAddress %2 "!LINE!"
        )
      )
    )
  )
)

del /q "%TEMP%\__gh_ns.tmp" >nul 2>nul
goto :EOF

:PrintAddress
REM "%1 = 记录类型A/AAAA, %2 = 原始行"
set "REC=%~1"
set "RAW=%~2"

set "WORK=%RAW%"
:TrimLead
if defined WORK if "!WORK:~0,1!"==" " set "WORK=!WORK:~1!" & goto :TrimLead

set "HEAD="
set "REST="
for /f "tokens=1* delims=:" %%a in ("!WORK!") do (
  set "HEAD=%%a"
  set "REST=%%b"
)

if /I "!HEAD!"=="Address" (
  set "CAND=!REST!"
) else if /I "!HEAD!"=="Addresses" (
  set "CAND=!REST!"
) else (
  set "CAND=!WORK!"
)

set "TMP=!CAND!"
:TrimLead2
if defined TMP if "!TMP:~0,1!"==" " set "TMP=!TMP:~1!" & goto :TrimLead2

for /f "tokens=1" %%i in ("!TMP!") do set "IPONLY=%%i"

REM "过滤 DNS 解析器自身 IP"
if /I "!IPONLY!"=="%DNS%" (
  goto :EOF
)

REM "去重 如果 SEEN_IPS 中已有该 IP 则跳过"
echo !SEEN_IPS! | findstr /I /C:" !IPONLY! " >nul && (
  REM duplicate skip
) 

 (
  set "SEEN_IPS=!SEEN_IPS!!IPONLY! "
  echo [%REC] !RAW!
)

goto :EOF