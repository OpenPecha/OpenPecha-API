from typing import Dict


def get_github_access_token(code: str) -> Dict:
    return {
        "access_token": "e72e16c7e42f292c6912e7710c838347ae178b4a",
        "scope": "repo,gist",
        "token_type": "bearer",
    }
