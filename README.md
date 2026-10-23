# code-daily

> Python 코드를 **타입이 한눈에 보이는 규칙적인 코드**로 정리하고, 그 코드를 읽어 **노션·블로그에 바로 올릴 글**로 만들어 주는 Claude Code 스킬

## 무엇을 하나요?

| 모드 | 명령 예시 | 하는 일 |
|---|---|---|
| `code` | `/code-daily code auth.py` | 파일 헤더, `# ===== 섹션 =====` 구분선, 모든 함수의 타입 힌트, docstring을 정해진 형식으로 붙입니다. **로직은 바꾸지 않고**, 개선점은 제안으로만 남깁니다. |
| `post` | `/code-daily post 261023_실습폴더` | 코드 구조(함수표: 입력 → 출력 타입)와 핵심 코드, 실행 방법, 배운 점을 담은 **개발자용 TIL 글**을 씁니다. 노션·Velog 공용이고, GitHub 블로그(Jekyll) 형식도 지원합니다. |
| `easy` | `/code-daily easy 실습폴더` | 일상 비유, 실제 값으로 따라가는 시나리오, 용어 풀이를 담은 **비개발자용 분석 글**을 씁니다. "기획자", "팀장님"처럼 독자를 말하면 그 독자가 정할 것을 체크리스트로 넣습니다. |
| `all` | `/code-daily all 실습폴더` | code로 정리한 뒤 이어서 post(또는 easy) 글까지 씁니다. |

슬래시 명령 없이 "TIL 써줘", "Velog 글로 정리해줘", "비개발자도 알아듣게 정리해줘"라고만 말해도 동작합니다.

### 글을 쓸 때 지키는 원칙
- 실행 결과는 실제로 돌려본 것만 씁니다. 화면이 없으면 `<!-- 📸 -->` 자리만 남깁니다.
- 공개 전에 API 키, 개인 경로, 이메일을 검사해서 가립니다.
- GitHub 블로그(Jekyll)용 글은 `{{ }}` / `{% %}`가 들어간 코드 블록을 `{% raw %}`로 감쌉니다.

## 설치

### 방법 1. Claude Code 플러그인 (권장)

Claude Code 안에서 입력합니다.

```text
/plugin marketplace add number6823/code-daily-skill
/plugin install code-daily@code-daily-skill
```

터미널에서 입력해도 됩니다.

```bash
claude plugin marketplace add number6823/code-daily-skill
claude plugin install code-daily@code-daily-skill
```

> 플러그인으로 설치하면 명령 이름 앞에 플러그인 이름이 붙어 `/code-daily:code-daily` 가 됩니다. 말로 요청하는 방식은 똑같이 동작합니다.

### 방법 2. skills CLI (Node.js 필요)

```bash
npx skills add number6823/code-daily-skill -g -y
```

`-g`는 사용자 전체에 설치하는 옵션이고, `-y`는 확인 질문을 건너뜁니다. 현재 프로젝트에만 설치하려면 `-g`를 빼세요.

### 방법 3. 직접 복사 (zip / git)

`code-daily.zip`을 받아서 스킬 폴더에 풉니다.

```powershell
# Windows PowerShell
Expand-Archive -Path "$HOME\Downloads\code-daily.zip" -DestinationPath "$HOME\.claude\skills" -Force
```

```bash
# macOS / Linux
unzip ~/Downloads/code-daily.zip -d ~/.claude/skills/
```

git으로 받는 방법도 있습니다.

```bash
git clone https://github.com/number6823/code-daily-skill.git
cp -r code-daily-skill/skills/code-daily ~/.claude/skills/
```

설치가 끝나면 `~/.claude/skills/code-daily/SKILL.md` 가 있어야 합니다.

### 설치 확인

Claude Code를 새로 시작한 뒤 `/code-daily`(플러그인이면 `/code-daily:code-daily`)를 입력해 자동완성 목록에 나오는지 봅니다.

## 요구 사항
- Claude Code
- Python 3.8 이상: 코드 뼈대 추출 스크립트 `scripts/outline.py` 용. 추가 패키지는 필요 없습니다.

## 업데이트 · 삭제

| 설치 방법 | 업데이트 | 삭제 |
|---|---|---|
| 플러그인 | `claude plugin marketplace update code-daily-skill` 후 `claude plugin update code-daily@code-daily-skill` | `claude plugin uninstall code-daily@code-daily-skill` |
| skills CLI | `npx skills update` | 설치된 `code-daily` 스킬 폴더 삭제 |
| 직접 복사 | 새 zip으로 덮어쓰기 | `~/.claude/skills/code-daily` 폴더 삭제 |

## 구성

```text
code-daily-skill/
├── .claude-plugin/
│   ├── marketplace.json   # /plugin marketplace add 가 읽는 목록
│   └── plugin.json        # 플러그인 정보
└── skills/code-daily/
    ├── SKILL.md           # 모드 선택과 작업 순서
    ├── references/
    │   ├── python-style.md   # code 모드 규칙 (타입·헤더·섹션·docstring)
    │   ├── post-guide.md     # post 모드 템플릿, 게시처별 차이, 공개 전 점검
    │   └── easy-guide.md     # easy 모드 템플릿, 타입 → 쉬운 말 번역표, 독자 역할 맞추기
    └── scripts/
        └── outline.py        # 코드 뼈대 추출 / 규칙 점검 (--check)
```
