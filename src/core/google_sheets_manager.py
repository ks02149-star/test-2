import os
import time
import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials
from src.config import CREDENTIALS_PATH
import requests

class GoogleSheetsManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GoogleSheetsManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._client = None
            cls._instance._last_auth_time = 0
            cls._instance.scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        return cls._instance

    def _authorize(self):
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError("credentials.json 파일을 찾을 수 없습니다.")
        self._creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, self.scopes)
        self._client = gspread.authorize(self._creds)
        self._last_auth_time = time.time()

    def get_client(self):
        """인증된 클라이언트를 반환합니다. 필요한 경우 자동 인증합니다."""
        # 45분마다 선제적 재인증 (토큰 만료 방지)
        if not self._client or (time.time() - self._last_auth_time > 45 * 60):
            self._authorize()
        return self._client

    def execute_with_retry(self, func, max_retries=3):
        """APIError (특히 401) 발생 시 재인증 후 재시도하는 래퍼입니다."""
        retries = 0
        while retries < max_retries:
            try:
                # 함수 실행 전 클라이언트가 유효한지 확인
                self.get_client()
                return func()
            except APIError as e:
                response = getattr(e, 'response', None)
                status_code = getattr(response, 'status_code', None) if response is not None else None
                
                # 401 Unauthorized 또는 권한 관련 에러 시 재인증
                if status_code in (401, 403) or retries < max_retries - 1:
                    retries += 1
                    time.sleep(1) # 잠시 대기 후 재시도
                    self._client = None # 클라이언트 초기화하여 다음 루프에서 재인증 유도
                    continue
                else:
                    raise e
            except Exception as e:
                # 기타 예외도 3번까지 재시도
                if retries < max_retries - 1:
                    retries += 1
                    time.sleep(1)
                    continue
                else:
                    raise e

    def get_worksheet(self, spreadsheet_id, sheet_name):
        """주어진 스프레드시트 ID와 시트 이름으로 워크시트를 가져옵니다."""
        def _get_sheet():
            client = self.get_client()
            return client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        return self.execute_with_retry(_get_sheet)

    def _get_drive_headers(self):
        """Google Drive API 요청을 위한 헤더를 반환합니다."""
        self.get_client() # 인증 갱신 확인
        if not hasattr(self, '_creds') or not self._creds:
            self._authorize()
        
        # access_token이 만료되었을 수 있으므로 갱신
        if self._creds.access_token_expired or not self._creds.access_token:
            import httplib2
            self._creds.refresh(httplib2.Http())
            
        token = self._creds.access_token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def search_drive_folder(self, folder_name, parent_id=None):
        """주어진 이름의 폴더를 검색하여 ID를 반환합니다."""
        def _search():
            headers = self._get_drive_headers()
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            params = {"q": query, "fields": "files(id, name)", "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
            res = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
            if res.status_code != 200:
                raise Exception(f"Search API Error: {res.text}")
            files = res.json().get('files', [])
            return files[0]['id'] if files else None
        return self.execute_with_retry(_search)

    def search_drive_file(self, file_name, parent_id=None, contains=False):
        """이름으로 파일(폴더 제외)을 검색하고 ID를 반환합니다."""
        def _search():
            headers = self._get_drive_headers()
            name_query = f"name contains '{file_name}'" if contains else f"name='{file_name}'"
            query = f"{name_query} and mimeType!='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            params = {"q": query, "fields": "files(id, name)", "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
            res = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
            if res.status_code != 200:
                raise Exception(f"Search File API Error: {res.text}")
            files = res.json().get('files', [])
            return files[0]['id'] if files else None
        return self.execute_with_retry(_search)

    def create_drive_folder(self, folder_name, parent_id=None):
        """새로운 폴더를 생성하고 ID를 반환합니다."""
        def _create():
            headers = self._get_drive_headers()
            data = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            if parent_id:
                data["parents"] = [parent_id]
            params = {"supportsAllDrives": "true"}
            res = requests.post("https://www.googleapis.com/drive/v3/files", headers=headers, json=data, params=params)
            if res.status_code != 200:
                raise Exception(f"Create Folder API Error: {res.text}")
            return res.json().get('id')
        return self.execute_with_retry(_create)
        
    def get_or_create_folder(self, folder_name, parent_id=None):
        """폴더가 존재하면 ID를 반환하고, 없으면 생성 후 반환합니다."""
        folder_id = self.search_drive_folder(folder_name, parent_id)
        if folder_id:
            return folder_id
        return self.create_drive_folder(folder_name, parent_id)

    def create_document_via_gas(self, template_id, new_name, root_folder_id, year_str, month_str):
        """GAS를 통해 폴더 생성과 파일 복사를 원스톱으로 처리합니다."""
        def _create():
            from src.config import GAS_WEB_APP_URL
            if not GAS_WEB_APP_URL:
                raise Exception("GAS_WEB_APP_URL이 설정되지 않았습니다.")
                
            data = {
                "templateId": template_id,
                "newName": new_name,
                "rootFolderId": root_folder_id,
                "yearStr": year_str,
                "monthStr": month_str
            }
            res = requests.post(GAS_WEB_APP_URL, json=data, allow_redirects=True)
            
            try:
                res_data = res.json()
                if res_data.get('success'):
                    return res_data.get('newFileId')
                else:
                    raise Exception(f"GAS Copy Error: {res_data.get('error')}")
            except Exception as e:
                raise Exception(f"GAS API Error ({res.status_code}): {res.text[:200]}... / {str(e)}")
        return self.execute_with_retry(_create)

    def stamp_document_via_gas(self, file_id, img_url):
        """GAS를 통해 권한 경고 없이 네이티브 셀 이미지(도장)를 삽입합니다."""
        def _stamp():
            from src.config import GAS_WEB_APP_URL
            if not GAS_WEB_APP_URL:
                raise Exception("GAS_WEB_APP_URL이 설정되지 않았습니다.")
                
            data = {
                "action": "stamp",
                "fileId": file_id,
                "imgUrl": img_url,
                "sheetName": "연차휴가신청서",
                "rangeA1": "W4"
            }
            res = requests.post(GAS_WEB_APP_URL, json=data, allow_redirects=True)
            
            try:
                res_data = res.json()
                if not res_data.get('success'):
                    raise Exception(f"GAS Stamp Error: {res_data.get('error')}")
            except Exception as e:
                raise Exception(f"GAS API Error ({res.status_code}): {res.text[:200]}... / {str(e)}")
        return self.execute_with_retry(_stamp)

    def request_approval_via_gas(self, payload):
        """GAS를 통해 사본 생성, 양식 채우기, 로그 기록을 한 번에 처리합니다."""
        def _request():
            from src.config import GAS_WEB_APP_URL
            if not GAS_WEB_APP_URL:
                raise Exception("GAS_WEB_APP_URL이 설정되지 않았습니다.")
                
            res = requests.post(GAS_WEB_APP_URL, json=payload, allow_redirects=True)
            
            try:
                res_data = res.json()
                if not res_data.get('success'):
                    raise Exception(f"GAS Approval Request Error: {res_data.get('error')}")
                return res_data.get('newFileId')
            except Exception as e:
                raise Exception(f"GAS API Error ({res.status_code}): {res.text[:200]}... / {str(e)}")
        return self.execute_with_retry(_request)
        
    def copy_drive_file(self, file_id, new_name, parent_id=None):
        """파일을 복사하고 새 파일의 ID를 반환합니다. GAS 웹앱 설정 시 이를 우선 사용합니다."""
        def _copy():
            from src.config import GAS_WEB_APP_URL
            
            # GAS 우회 방법 (용량 제한 회피용)
            if GAS_WEB_APP_URL:
                data = {
                    "fileId": file_id,
                    "newName": new_name,
                    "parentId": parent_id
                }
                # GAS는 리다이렉션을 발생시킬 수 있으므로 allow_redirects=True 처리됨 (requests 기본)
                res = requests.post(GAS_WEB_APP_URL, json=data)
                
                # GAS가 HTML을 반환하는 등 예외적인 상황 대비
                try:
                    res_data = res.json()
                    if res_data.get('success'):
                        return res_data.get('newFileId')
                    else:
                        raise Exception(f"GAS Copy Error: {res_data.get('error')}")
                except Exception as e:
                    raise Exception(f"GAS API Error ({res.status_code}): {res.text[:200]}... / {str(e)}")

            # 기본 구글 드라이브 API 방법
            headers = self._get_drive_headers()
            data = {"name": new_name}
            if parent_id:
                data["parents"] = [parent_id]
            params = {"supportsAllDrives": "true"}
            res = requests.post(f"https://www.googleapis.com/drive/v3/files/{file_id}/copy", headers=headers, json=data, params=params)
            if res.status_code != 200:
                raise Exception(f"Copy API Error ({res.status_code}): {res.text}")
            return res.json().get('id')
        return self.execute_with_retry(_copy)
        
    def rename_and_move_file(self, file_id, new_name=None, add_parents=None, remove_parents=None):
        """파일 이름을 변경하거나 폴더를 이동합니다."""
        def _update():
            headers = self._get_drive_headers()
            data = {}
            if new_name:
                data["name"] = new_name
            params = {"supportsAllDrives": "true"}
            if add_parents:
                params["addParents"] = add_parents
            if remove_parents:
                params["removeParents"] = remove_parents
            res = requests.patch(f"https://www.googleapis.com/drive/v3/files/{file_id}", headers=headers, json=data, params=params)
            if res.status_code != 200:
                raise Exception(f"Rename/Move API Error: {res.text}")
            return res.json()
        return self.execute_with_retry(_update)
        
    def get_file_web_content_link(self, file_id):
        """이미지 등의 파일에 대한 다운로드/표시용 웹 링크를 가져옵니다."""
        def _get():
            headers = self._get_drive_headers()
            params = {"fields": "webContentLink, webViewLink", "supportsAllDrives": "true"}
            res = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}", headers=headers, params=params)
            if res.status_code != 200:
                raise Exception(f"Get Link API Error: {res.text}")
            return res.json().get('webContentLink') or f"https://drive.google.com/uc?id={file_id}"
        return self.execute_with_retry(_get)
