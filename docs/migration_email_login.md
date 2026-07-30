# 학번 제거 / 이메일 로그인 전환 — 운영 반영 절차

## ⚠️ 먼저 읽을 것

이번 마이그레이션 체인은 **의도적으로 파괴적(destructive)** 이다. 빈 DB 에 순서대로 적용되는 것을
전제로 설계했고, 데이터는 마이그레이션이 아니라 **덤프 → 변환 → 재적재** 로 옮긴다.

| 마이그레이션 | 하는 일 |
|---|---|
| `library.0013_drop_manager_fks` | Book/Loan/Notice 의 FK 컬럼 **삭제** |
| `manager.0002_delete_manager` | `MANAGER` 테이블 **DROP** |
| `members.0005_email_login` | `MEMBER.sid`(PK), `username`, M2M 중간 테이블 **삭제** |
| `manager.0003_recreate_manager` | MANAGER 재생성 (PK = member_id) |
| `library.0014_restore_manager_fks` | FK 컬럼 복원 |

**`render.yaml` 의 `buildCommand` 에 `python manage.py migrate` 가 들어 있다.**
즉 **main 에 push 하면 Render 가 자동 배포되면서 위 체인을 운영 DB 에 그대로 실행한다.**
아래 절차대로 백업을 먼저 뜨지 않고 push 하면 **회원·대출·관리자 데이터가 소실된다.**

## 사전 확인

기존 회원 중 이메일이 비어 있거나 중복이면 이관이 실패한다. 먼저 확인한다.

```bash
python manage.py shell -c "
from members.models import Member
from django.db.models import Count
print('전체:', Member.objects.count())
print('이메일 없음:', Member.objects.filter(email='').count())
print('중복 이메일:', list(Member.objects.values('email').annotate(n=Count('email')).filter(n__gt=1)))
"
```

`email` 은 이미 `unique=True` 라 중복은 없어야 정상이지만, 빈 값이 있으면 먼저 채워야 한다.

## 절차

### 1. Neon 브랜치로 리허설

Neon 콘솔에서 운영 브랜치(`main`)로부터 새 브랜치(예: `email-login-rehearsal`)를 만든다.
브랜치는 copy-on-write 라 즉시 생성되고 운영에 영향이 없다. 브랜치의 연결 문자열을 받아둔다.

```bash
export DATABASE_URL='<브랜치 연결 문자열>'
```

### 2. 구 스키마에서 덤프

**아직 새 코드로 체크아웃하지 않은 상태**(= 이 커밋 이전)에서 실행해야 한다.

```bash
git stash            # 또는 이전 커밋으로 체크아웃
python manage.py dumpdata members manager library \
  --natural-foreign --indent 2 -o backup_old.json
```

`backup_old.json` 은 학번이 그대로 들어 있는 개인정보 파일이다. **저장소에 커밋하지 말고**,
이관 검증이 끝나면 삭제한다.

### 3. 변환

```bash
git stash pop        # 새 코드로 복귀
python tools/convert_fixture_email_login.py backup_old.json backup_new.json
```

학번을 1부터 시작하는 새 `id` 로 재매핑하고, 참조를 모두 따라 바꾼다.
매핑되지 않는 회원 참조가 하나라도 있으면 스크립트가 중단되므로 그때는 진행하지 말 것.

### 4. 스키마 재생성 후 적재

```bash
python manage.py migrate
python manage.py loaddata backup_new.json
```

### 5. 검증

```bash
python manage.py shell -c "
from members.models import Member
from manager.models import Manager
from library.models import Loan
print('회원', Member.objects.count(), '관리자', Manager.objects.count(), '대출', Loan.objects.count())
print('관리자 소속:', [(m.pk, m.member.email) for m in Manager.objects.all()][:5])
print('대출 연결 정상:', all(l.member_id and l.book_id for l in Loan.objects.all()))
"
```

건수가 2단계 덤프와 일치하는지, 기존 비밀번호로 로그인되는지 확인한다.
(비밀번호 해시는 그대로 이관되므로 **기존 회원은 이메일 + 기존 비밀번호로 로그인된다.**)

### 6. 운영 반영

리허설이 성공하면 같은 절차를 운영 브랜치에 적용한다. 순서가 중요하다.

1. Neon 에서 운영 브랜치 **백업 스냅샷** 생성 (롤백 지점)
2. Render 서비스 **일시 중지** (배포 중 쓰기 차단)
3. 2~4단계를 운영 DB 대상으로 실행
4. main 에 push → Render 재배포
   - 이때 `migrate` 는 이미 적용된 상태라 no-op 이 된다
5. 로그인/가입/대출 조회 스모크 테스트

### 롤백

Neon 브랜치를 5단계 이전 시점으로 **restore** 하고, 코드를 이전 커밋으로 되돌린 뒤 재배포한다.
Neon 의 point-in-time restore 가 가장 빠른 복구 수단이다.

## 이관 후 달라지는 것

- **로그인 ID 가 학번 → 이메일** 로 바뀐다. 기존 회원에게 공지 필요.
- **기존에 발급된 JWT 는 모두 무효**가 된다 (`USER_ID_FIELD` 가 `sid` → `id` 로 변경).
  로그인된 사용자는 한 번 다시 로그인해야 한다.
- 관리자 페이지에서 회원 검색이 학번 대신 **이름/이메일** 기준이 된다.
- `MEMBER` 테이블에 학번 컬럼이 존재하지 않으므로, 이후 학번은 어디에도 저장되지 않는다.
