import httpx
from pydantic import SecretStr
from .models import Settings

def _raise_on_4xx_5xx(response):
    response.raise_for_status()

class BaseApiClient:
    def __init__(self, session: httpx.Client) -> None:
        self.session = session

class AIFolder(BaseApiClient):
    def new_name(self):
        pass
    def rename(self):
        pass
    def delete(self):
        pass
    def change_folder(self):
        pass

class AI(BaseApiClient):
    def get(self, ai_id: int):
        r = self.session.get(f"/ai/get/{ai_id}")
        return r.json()

    def get_farmer_ais(self):
        r = self.session.get("/ai/get-farmer-ais")
        return r.json()

    def sync(self, ais: str):
        raise NotImplemented

    def test_scenario(self, ai_id: int, scenario_id: int = 0):
        r = self.session.post(f"/ai/test-scenario/", json={"scenario_id": scenario_id, "ai_id": ai_id })
        return r.json()

    def save(self, ai_id: int, code: str):
        r = self.session.post("/ai/save", json={"ai_id": ai_id, "code": code})
        return r.json()

class Fight(BaseApiClient):
    def get(self, fight: int):
        r = self.session.get(f"/fight/get/{fight}")
        return r.json()

    def get_logs(self, fight: int):
        r = self.session.get(f"/fight/get-logs/{fight}")
        return r.json()

class Encyclopedia(BaseApiClient):
    def get(self, code: str, language: str = 'en'):
        r = self.session.get(f"/encyclopedia/get/{language}/{code}")
        return r.json()

    def search(self, query: str, page: int = 0, language: str = 'en'):
        r = self.session.get(f"/encyclopedia/search/{language}/{query}/{page}")
        return r.json()

    def get_all_locale(self, language: str = 'en'):
        r = self.session.get(f"/encyclopedia/get-all-locale/{language}")
        return r.json() 

class Function(BaseApiClient):
    def get_all(self):
        r = self.session.get("/function/get-all")
        return r.json()

    def get_categories(self):
        r = self.session.get("/function/get-categories")
        return r.json()
    
    def doc(self, language: str = 'en'):
        r = self.session.get(f"/function/doc/{language}")
        return r.json()

class Constant(BaseApiClient):
    def get_all(self):
        r = self.session.get("/constant/get-all")
        return r.json()

class Leek(BaseApiClient):
    def get_private(self, leek_id: int):
        r = self.session.get(f"/leek/get-private/{leek_id}")
        return r.json()

    def set_ai(self, leek_id: int, ai_id: int):
        r = self.session.post(f"/leek/set-ai", json={'leek_id': leek_id, 'ai_id': ai_id})
        return r.json()        

class Farmer(BaseApiClient):
    def get_from_token(self):
        r = self.session.get("/farmer/get-from-token")
        return r.json()

class LeekWars:
    '''
    LeekWars API Client

    https://leekwars.com/help/api/
    '''

    def __init__(self, settings: Settings | None = None) -> None:
        self.session = httpx.Client(
            base_url="https://leekwars.com/api/",
            event_hooks={'response': [_raise_on_4xx_5xx]}
        )
        self.settings = settings

        self.leek = Leek(self.session)
        self.farmer = Farmer(self.session)
        self.function = Function(self.session)
        self.constant = Constant(self.session)
        self.encyclopedia = Encyclopedia(self.session)
        self.fight = Fight(self.session)
        self.ai = AI(self.session)
        self.ai_folder = AIFolder(self.session)

        if self.settings:
            self.login(settings.username, settings.password)

    def login(self, username: str, password: SecretStr):
        r = self.session.post(
            '/farmer/login-token',
            json={
                'login': username,
                'password': password.get_secret_value()
            }
        )

        self.session.cookies = { 'token': r.json()['token'] }
        return True

    def version(self):
        r = self.session.get('/leek-wars/version')
        return r.json()
