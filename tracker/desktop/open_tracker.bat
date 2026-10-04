@echo off
chcp 65001 >nul
cd /d "%~dp0.."
git pull --quiet 2>nul
start "" "%cd%\greenbean.html"
