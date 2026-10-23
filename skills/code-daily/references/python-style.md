# code-daily Python 작성 규칙

이 규칙의 목적은 두 가지다.
1. 사람이 함수 이름과 시그니처만 보고 "무엇을 받아서 무엇을 돌려주는지" 바로 알게 한다.
2. `scripts/outline.py` 가 코드를 기계적으로 읽어 블로그 글의 구조표를 만들 수 있게 한다.
   그래서 아래 형식(헤더 docstring, 섹션 구분선, docstring 첫 줄)은 **글자 그대로** 지킨다. 형식이 흔들리면 추출이 빠진다.

## 목차
1. 파일 헤더
2. import 순서
3. 섹션 구분선
4. 타입 힌트 (Python 버전별 주의)
5. docstring
6. 이름 짓기
7. 함수 크기와 실행부
8. 완성 예시

---

## 1. 파일 헤더

모든 파일 맨 위에 모듈 docstring 을 둔다. 첫 줄이 블로그 글에서 그 파일의 제목이 된다.

```python
"""
auth.py — 회원가입·로그인 인증 모듈

요약: SQLite 에 사용자 계정을 저장하고 PBKDF2 해시로 비밀번호를 검증한다.
사용: from auth import register, login
"""
```

- 첫 줄: `<파일명> — <한 줄 제목>` (em dash `—`)
- `요약:` 2~3줄. 무엇을, 어떤 방식으로.
- `사용:` 실행 명령(`streamlit run app.py`, `python train.py --epochs 10`) 또는 import 예시.

## 2. import 순서

`__future__` → 표준 라이브러리 → 서드파티 → 로컬 모듈. 그룹 사이에 빈 줄 하나.

## 3. 섹션 구분선

파일 안을 성격별로 나눈다. 형식은 정확히 `# ===== 이름 =====` (`=` 3개 이상).

권장 순서 (해당하는 것만 쓴다):

| 섹션 | 내용 |
|---|---|
| `설정` | 상수, 경로, 하이퍼파라미터 |
| `타입` | TypedDict, dataclass, NamedTuple, 타입 별칭 |
| 도메인 이름 (`DB`, `인증`, `전처리`, `검출`, `검색` …) | 실제 로직. 여러 개 가능 |
| `UI` | Streamlit/Gradio 화면 함수 |
| `실행` | `main()` 과 `if __name__ == "__main__":` |

함수가 2개 이하인 아주 짧은 파일은 섹션을 생략해도 된다.

## 4. 타입 힌트

**모든 함수의 매개변수와 반환값에 타입을 적는다.** 반환이 없으면 `-> None` 까지 적는다. `self`, `cls` 는 생략.
모듈 상수는 `Final` 로 적는다: `ITERATIONS: Final[int] = 200_000`.

### Python 버전 먼저 확인

작업 전에 `python --version` 을 확인한다. 문법이 버전마다 다르고, 틀리면 실행 순간 에러가 나기 때문이다.

| 버전 | 쓰는 법 |
|---|---|
| 3.10 이상 | `str \| None`, `list[str]`, `dict[str, int]` 그대로 사용 |
| 3.7 ~ 3.9 | 파일 맨 위에 `from __future__ import annotations` 를 넣으면 **어노테이션 안에서는** `list[str]`, `str \| None` 사용 가능 |

3.7~3.9 에서 `__future__` 로도 안 되는 곳 — 어노테이션이 아니라 **실행되는 코드**인 자리:
- 타입 별칭 대입: `Box = list[float]` ✗ → `Box = List[float]` (typing 에서 import)
- `cast(...)`, `isinstance(...)` 인자
- Pydantic v1, Typer, FastAPI 처럼 런타임에 어노테이션을 평가하는 라이브러리의 모델/함수 → `Optional[str]`, `List[str]` 사용

### 구체적인 타입을 고른다

- `Any` 는 정말 아무거나 올 때만. `dict` 하나로 뭉뚱그리지 말고 키가 정해진 dict 는 `TypedDict` 로.
- 원소가 3개 이상인 tuple 반환, 또는 원소 의미가 헷갈리는 tuple 은 `NamedTuple` / `dataclass` 로 이름을 붙인다.
  `tuple[bool, str]` 정도는 그대로 두되 docstring `Returns:` 에 각 자리의 의미를 적는다.
- 자주 쓰는 라이브러리 타입: `np.ndarray`, `PIL.Image.Image`, `pd.DataFrame`, `torch.Tensor`, `pathlib.Path`, `sqlite3.Connection`.
- 파일 경로는 `str | Path` 로 받고 내부에서 `Path(...)` 로 바꾼다.

### TypedDict 예시 — 키 이름이 예약어일 때

YOLO 검출 결과처럼 키에 `class` 가 들어가면 클래스 문법을 못 쓴다. 함수형 문법을 쓴다.

```python
Detection = TypedDict("Detection", {"class": str, "conf": float, "bbox": List[float]})


class DetectionResult(TypedDict):
    schema_version: str
    image_id: str
    model: str
    detections: List[Detection]
```

## 5. docstring

공개 함수·클래스에는 docstring 을 단다. **첫 줄은 "~한다." 로 끝나는 한 문장** — 블로그 함수표의 "설명" 칸에 그대로 들어간다.

```python
def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """비밀번호를 salt 와 함께 PBKDF2-SHA256 으로 해싱한다.

    Args:
        salt: 없으면 16바이트를 새로 만든다. 로그인 검증 때는 저장된 salt 를 넘긴다.

    Returns:
        (salt, 해시) — 둘 다 DB 에 저장해야 다음 검증이 가능하다.
    """
```

- 타입은 이미 시그니처에 있으므로 docstring 에 반복하지 않는다.
- `Args:` / `Returns:` / `Raises:` 는 이름만으로 뻔하지 않을 때만 쓴다.
- `_` 로 시작하는 내부 함수는 한 줄 docstring 이면 충분하다.

## 6. 이름 짓기

| 대상 | 규칙 | 예 |
|---|---|---|
| 함수 | `동사_목적어` | `load_image`, `hash_password`, `build_prompt` |
| bool 변수/함수 | `is_`, `has_`, `can_` | `is_valid`, `has_detections` |
| 상수 | `UPPER_SNAKE` | `CONF_THRESHOLD`, `DB_PATH` |
| 내부용 | 앞에 `_` | `_crop_roi` |
| 클래스·타입 | `PascalCase` | `Detection`, `SearchHit` |

약어(`img`, `cfg`)는 프로젝트 안에서 한 가지로 통일한다.

## 7. 함수 크기와 실행부

- 함수 하나는 일 하나. 40줄을 넘기면 쪼갤 수 있는지 본다.
- 스크립트로 실행하는 파일은 `def main() -> None:` + `if __name__ == "__main__": main()`.
- Streamlit 앱은 위에서 아래로 실행되므로 main 가드 없이 `# ===== 실행 =====` 섹션 아래에 화면 분기 코드를 둬도 된다.
- 주석은 "무엇"이 아니라 "왜"가 필요한 곳에만 단다. 코드를 그대로 읽어주는 주석은 지운다.

---

## 8. 완성 예시

규칙을 모두 적용한 파일. (Python 3.8 기준이라 `__future__` 와 `typing.Final` 사용)

```python
"""
auth.py — 회원가입·로그인 인증 모듈

요약: SQLite 에 사용자 계정을 저장하고 PBKDF2 해시로 비밀번호를 검증한다.
사용: from auth import register, login
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from typing import Final

# ===== 설정 =====

DB_PATH: Final[str] = os.path.join(os.path.dirname(__file__), "users.db")
ITERATIONS: Final[int] = 200_000

# ===== DB =====


def get_conn() -> sqlite3.Connection:
    """DB 에 연결하고, users 테이블이 없으면 만든다."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            salt     BLOB NOT NULL,
            pw_hash  BLOB NOT NULL
        )
        """
    )
    return conn

# ===== 인증 =====


def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """비밀번호를 salt 와 함께 PBKDF2-SHA256 으로 해싱한다.

    Returns:
        (salt, 해시)
    """
    if salt is None:
        salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return salt, pw_hash


def login(username: str, password: str) -> bool:
    """아이디·비밀번호가 맞으면 True 를 반환한다."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT salt, pw_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        return False

    salt, stored_hash = row
    _, pw_hash = hash_password(password, salt)
    # 일반 == 비교는 앞자리부터 다르면 빨리 끝나서 응답 시간으로 해시를 추측당할 수 있다
    return hmac.compare_digest(pw_hash, stored_hash)
```
