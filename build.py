import os
import sys
import shutil
import subprocess

def main():
    print("========================================================")
    print("푸름애드 관리프로그램 완벽 배포용 빌드 스크립트")
    print("========================================================")
    print()

    print("1. 패키징에 필요한 도구들을 설치합니다...")
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    if os.path.exists("requirements.txt"):
        subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Install additional required packages
    subprocess.call([sys.executable, "-m", "pip", "install", "PyQt5", "PyQtWebEngine", "PyQt-Fluent-Widgets", "selenium", "pandas", "openpyxl", "gspread", "oauth2client", "webdriver-manager"])

    print("\n2. 기존 빌드 찌꺼기 청소...")
    if os.path.exists("build"):
        shutil.rmtree("build", ignore_errors=True)
    if os.path.exists("dist"):
        shutil.rmtree("dist", ignore_errors=True)
    for f in os.listdir("."):
        if f.endswith(".spec"):
            try:
                os.remove(f)
            except:
                pass

    print("\n3. 단일 실행파일(.exe) 생성 시작! (잠시만 기다려주세요...)")
    pyinstaller_args = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "푸름애드_관리프로그램",
        "--add-data", f"assets{os.pathsep}assets/",
        "--add-data", f"Font{os.pathsep}Font/",
        "--collect-all", "qfluentwidgets",
        "--collect-all", "selenium",
        "--collect-all", "webdriver_manager",
        "--hidden-import", "PyQt5.QtWebEngineWidgets",
        "--hidden-import", "pandas",
        "--hidden-import", "openpyxl",
        "--hidden-import", "gspread",
        "--hidden-import", "oauth2client",
        "src/main.py"
    ]
    
    subprocess.check_call(pyinstaller_args)

    print("\n4. 프로그램과 함께 배포해야 할 기본 파일 복사 중...")
    if not os.path.exists("dist"):
        os.makedirs("dist")
    
    if os.path.exists("credentials.json"):
        shutil.copy2("credentials.json", "dist/credentials.json")
    if os.path.exists("키워드_순위_작업표.xlsx"):
        shutil.copy2("키워드_순위_작업표.xlsx", "dist/키워드_순위_작업표.xlsx")

    print("\n========================================================")
    print("빌드가 성공적으로 완료되었습니다!")
    print("[배포 방법]")
    print("1. 현재 폴더에 생긴 'dist' 폴더 안으로 들어가세요.")
    print("2. 그 안에 있는 파일들을 압축(Zip)하여 다른 컴퓨터에 전달하시면 됩니다.")
    print("   - 푸름애드_관리프로그램.exe (본체)")
    print("   - credentials.json (구글 시트 연동 파일, 있는 경우에만)")
    print("   - 키워드_순위_작업표.xlsx (있는 경우에만)")
    print()
    print("* 다른 사람 컴퓨터에 파이썬이 설치되어 있지 않아도 완벽하게 작동합니다!")
    print("========================================================")

if __name__ == "__main__":
    main()
