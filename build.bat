@echo off
chcp 65001 >nul
echo ========================================================
echo 푸름애드 관리프로그램 빌드 스크립트 (PyInstaller)
echo ========================================================
echo.

echo 1. PyInstaller 설치 확인 중...
pip install pyinstaller >nul 2>&1

echo 2. 기존 빌드 폴더 삭제 중 (초기화)...
if exist "build" rmdir /s /q "build"
if exist "dist\푸름애드_관리프로그램" rmdir /s /q "dist\푸름애드_관리프로그램"
if exist "main.spec" del /q "main.spec"

echo 3. PyInstaller 패키징 시작...
pyinstaller --noconfirm --onedir --windowed --noconsole --name "푸름애드_관리프로그램" --icon "assets\images\logo.ico" --hidden-import "PyQt5.QtWebEngineWidgets" --hidden-import "webdriver_manager" --hidden-import "selenium" --hidden-import "pandas" --hidden-import "openpyxl" --hidden-import "gspread" --hidden-import "oauth2client" "src\main.py"

echo.
echo 4. 필수 외부 자산 복사 중...

xcopy "assets" "dist\푸름애드_관리프로그램\assets" /E /I /H /Y >nul
xcopy "Font" "dist\푸름애드_관리프로그램\Font" /E /I /H /Y >nul
copy /Y "키워드_순위_작업표.xlsx" "dist\푸름애드_관리프로그램\" >nul

echo.
echo ========================================================
echo 빌드가 성공적으로 완료되었습니다!
echo 배포 방법:
echo 1. 현재 폴더 안의 'dist' 폴더 안에 들어가시면 '푸름애드_관리프로그램' 폴더가 있습니다.
echo 2. 해당 폴더('푸름애드_관리프로그램')를 통째로 압축(zip)하여 다른 PC로 전달하시면 됩니다.
echo 3. 전달받은 PC에서는 압축을 풀고 그 안의 '푸름애드_관리프로그램.exe'를 실행하면 되며,
echo    같은 폴더에 '키워드_순위_작업표.xlsx'도 함께 들어있어 바로 사용 가능합니다.
echo ========================================================
pause
