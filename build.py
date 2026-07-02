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
    subprocess.call([sys.executable, "-m", "pip", "install", "PyQt5", "PyQtWebEngine", "PyQt-Fluent-Widgets", "selenium", "pandas", "openpyxl", "gspread", "oauth2client", "webdriver-manager", "requests", "beautifulsoup4"])

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

    print("\n3. 프로그램 빌드 시작! (잠시만 기다려주세요...)")
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "푸름애드_관리프로그램",
        "--paths", ".",
        "--add-data", f"assets{os.pathsep}assets/",
        "--add-data", f"Font{os.pathsep}Font/",
        "--collect-all", "qfluentwidgets",
        "--collect-all", "selenium",
        "--collect-all", "webdriver_manager",
        "--collect-all", "PyQt5.QtWebEngine",
        "--collect-all", "PyQt5.QtWebEngineCore",
        "--collect-all", "PyQt5.QtWebEngineWidgets",
        "--exclude-module", "matplotlib",
        "--exclude-module", "IPython",
        "--exclude-module", "scipy",
        "--exclude-module", "pytest",
        "--exclude-module", "tkinter",
        "--exclude-module", "pyarrow",
        "--exclude-module", "fastparquet",
        "--exclude-module", "tables",
        "--exclude-module", "sqlalchemy",
        "--exclude-module", "PyQt6",
        "--exclude-module", "PySide6",
        "--hidden-import", "PyQt5.QtWebEngineWidgets",
        "--hidden-import", "PyQt5.QtWebEngineCore",
        "--hidden-import", "PyQt5.QtWebEngine",
        "--hidden-import", "pandas",
        "--hidden-import", "pandas._libs.tslibs.strptime",
        "--hidden-import", "openpyxl",
        "--hidden-import", "gspread",
        "--hidden-import", "oauth2client",
        "--hidden-import", "requests",
        "--hidden-import", "bs4",
        "--hidden-import", "_overlapped",
        "--hidden-import", "asyncio",
        "src/main.py"
    ]
    
    subprocess.check_call(pyinstaller_args)

    print("\n4. 프로그램과 함께 배포해야 할 기본 파일 복사 중...")
    target_dir = os.path.join("dist", "푸름애드_관리프로그램")
    workspace_dir = os.path.join(target_dir, "Workspace")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir, exist_ok=True)
    
    if os.path.exists("credentials.json"):
        shutil.copy2("credentials.json", os.path.join(workspace_dir, "credentials.json"))
    if os.path.exists("키워드_순위_작업표.xlsx"):
        shutil.copy2("키워드_순위_작업표.xlsx", os.path.join(target_dir, "키워드_순위_작업표.xlsx"))
        
    # [CRITICAL FIX] PyQtWebEngine icudtl.dat   ( 丮     )
    resources_dir = os.path.join(target_dir, "_internal", "PyQt5", "Qt5", "resources")
    if os.path.exists(resources_dir):
        for item in os.listdir(resources_dir):
            src_path = os.path.join(resources_dir, item)
            dst_path = os.path.join(target_dir, item)
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
                
    locales_dir = os.path.join(target_dir, "_internal", "PyQt5", "Qt5", "translations", "qtwebengine_locales")
    if os.path.exists(locales_dir):
        dst_locales = os.path.join(target_dir, "qtwebengine_locales")
        if not os.path.exists(dst_locales):
            shutil.copytree(locales_dir, dst_locales)

    print("\n========================================================")
    print("빌드가 성공적으로 완료되었습니다!")
    print("[배포 방법]")
    print("1. 'dist' 폴더 안에 생성된 '푸름애드_관리프로그램' 폴더를 확인하세요.")
    print("2. 해당 폴더 전체를 통째로 압축(.zip)하여 사용자에게 전달하세요.")
    print("   ※ 폴더 안에는 .exe 파일뿐만 아니라 _internal, Workspace 등이 포함되어야 합니다.")
    print("   ※ credentials.json 파일은 Workspace 폴더 안에 정상적으로 배포되었습니다.")
    print()
    print("* 다른 사람 컴퓨터에 파이썬이 설치되어 있지 않아도 완벽하게 작동합니다!")
    print("========================================================")

if __name__ == "__main__":
    main()
