import os
import sys
import shutil
import subprocess

def main():
    print("========================================================")
    print("푸름애드 관리프로그램 빌드 스크립트 (PyInstaller)")
    print("========================================================")
    print()

    print("1. PyInstaller 설치 확인 중...")
    subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("2. 기존 빌드 폴더 삭제 중 (초기화)...")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist/푸름애드_관리프로그램"):
        shutil.rmtree("dist/푸름애드_관리프로그램")
    if os.path.exists("main.spec"):
        os.remove("main.spec")

    print("3. PyInstaller 패키징 시작...")
    pyinstaller_args = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--noconsole",
        "--name", "푸름애드_관리프로그램",
        "--paths", ".",
        "--collect-all", "selenium",
        "--collect-all", "webdriver_manager",
        "--hidden-import", "PyQt5.QtWebEngineWidgets",
        "--hidden-import", "pandas",
        "--hidden-import", "openpyxl",
        "--hidden-import", "gspread",
        "--hidden-import", "oauth2client",
        "src/main.py"
    ]
    
    # Run pyinstaller via subprocess
    subprocess.check_call(pyinstaller_args)

    print("\n4. 필수 외부 자산 복사 중...")
    target_dir = "dist/푸름애드_관리프로그램"
    
    if os.path.exists("assets"):
        shutil.copytree("assets", os.path.join(target_dir, "assets"), dirs_exist_ok=True)
    if os.path.exists("Font"):
        shutil.copytree("Font", os.path.join(target_dir, "Font"), dirs_exist_ok=True)
    if os.path.exists("키워드_순위_작업표.xlsx"):
        shutil.copy2("키워드_순위_작업표.xlsx", target_dir)
    if os.path.exists("credentials.json"):
        shutil.copy2("credentials.json", target_dir)

    print("\n========================================================")
    print("빌드가 성공적으로 완료되었습니다!")
    print("배포 방법:")
    print("1. 현재 폴더 안의 'dist' 폴더 안에 들어가시면 '푸름애드_관리프로그램' 폴더가 있습니다.")
    print("2. 해당 폴더('푸름애드_관리프로그램')를 통째로 압축(zip)하여 다른 PC로 전달하시면 됩니다.")
    print("3. 전달받은 PC에서는 압축을 풀고 그 안의 '푸름애드_관리프로그램.exe'를 실행하면 되며,")
    print("   같은 폴더에 '키워드_순위_작업표.xlsx'도 함께 들어있어 바로 사용 가능합니다.")
    print("========================================================")

if __name__ == "__main__":
    main()
