@echo off
chcp 65001 >nul
REM ==========================================
REM AI Auto Renovation Assistant - CORS Test Script (Windows)
REM ==========================================
REM Purpose: Verify CORS requests and Authorization header support
REM Environment: Windows CMD
REM ==========================================

setlocal enabledelayedexpansion

set BASE_URL=https://ai-gateway-show.yunzhonghe.com/ecom_reco_agent
set ORIGIN=http://localhost:3000
set AUTH_HEADER=Authorization: Bearer test-token-123

echo.
echo =========================================
echo AI Auto Renovation Assistant - CORS Test
echo =========================================
echo.
echo Test URL: %BASE_URL%
echo Origin: %ORIGIN%
echo.

echo =========================================
echo Test 1: OPTIONS Preflight Request (with Authorization)
echo =========================================
echo.
echo Checking if browser can send CORS request with Authorization header...
echo.
curl -i -X OPTIONS ^
  -H "Origin: %ORIGIN%" ^
  -H "Access-Control-Request-Method: POST" ^
  -H "Access-Control-Request-Headers: authorization,content-type" ^
  "%BASE_URL%/agents/ecom-reco-agent/runs"

echo.
echo.
echo =========================================
echo Test 2: Health Check (GET with Authorization)
echo =========================================
echo.
echo Checking GET request with Authorization header...
echo.
curl -i ^
  -H "Origin: %ORIGIN%" ^
  -H "%AUTH_HEADER%" ^
  "%BASE_URL%/health"

echo.
echo.
echo =========================================
echo Test 3: Main API Endpoint (OPTIONS)
echo =========================================
echo.
echo Checking CORS preflight for main API endpoint...
echo.
curl -i -X OPTIONS ^
  -H "Origin: %ORIGIN%" ^
  -H "Access-Control-Request-Method: POST" ^
  -H "Access-Control-Request-Headers: authorization,content-type" ^
  "%BASE_URL%/agents/ecom-reco-agent/runs"

echo.
echo.
echo =========================================
echo Test 4: Sessions List (GET)
echo =========================================
echo.
echo Checking CORS support for sessions endpoint...
echo.
curl -i ^
  -H "Origin: %ORIGIN%" ^
  "%BASE_URL%/sessions"

echo.
echo.
echo =========================================
echo Test Completed
echo =========================================
echo.
echo Verification Points:
echo 1. OPTIONS request should return 204/200 with CORS headers
echo 2. Health check should return 200 with CORS headers
echo 3. Response headers should include:
echo    - Access-Control-Allow-Origin: * or specific domain
echo    - Access-Control-Allow-Headers: authorization, content-type
echo    - Access-Control-Allow-Methods: POST, GET, OPTIONS
echo    - Access-Control-Allow-Credentials: true (if credentials allowed)
echo.
pause
