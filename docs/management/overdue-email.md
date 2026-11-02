# 연체 안내 메일 수동 발송

## 사용 순서

1. Django 관리자 → **대출 기록 목록**에서 안내할 대출을 선택합니다.
2. 작업에서 **연체 안내 메일 발송 (언어 선택·미리보기)**을 실행합니다.
3. **한국어** 또는 **Deutsch (독일어)**를 선택하고 **미리보기 갱신**을 누릅니다.
4. 보내는 주소, 회신 주소, 회원별 수신 주소·제목·본문을 확인합니다.
5. **확인한 N명에게 메일 발송**을 눌러 발송합니다.

같은 회원의 선택된 연체 도서는 한 통으로 묶고, 회원마다 개별 메일을 보냅니다. 반납이 끝난 도서, 반납 예정일이 오늘 이후인 도서, 예정일이 없는 도서, 유효한 수신 이메일이 없는 도서는 제외합니다. 날짜는 한국 시간 기준이며, 오늘이 반납 예정일인 도서는 포함하지 않습니다.

발송 전 언어·대상·이메일·본문 등이 달라지면 미리보기를 갱신하고 다시 확인하도록 안내합니다. 미리보기는 30분간 유효합니다. 같은 확인 요청을 재전송해도 다시 발송하지 않습니다. 새로 선택해 미리보기를 시작하면 별도의 발송 요청이 되므로, 의도적으로 다시 안내할 때 사용합니다.

메일 서버에서 접수한 기록은 해당 대출의 **이력**에 남습니다. **연체 안내 메일 발송 기록**에서는 관리자·수신 주소·언어·처리 결과를 확인할 수 있습니다. 기록 화면 접근이 필요한 일반 관리자에게는 해당 모델의 조회 권한을 부여합니다. 대출의 변경 권한이 있어야 발송 작업을 실행할 수 있습니다.

## 발신 계정 설정

발송 계정과 메일 서비스는 도서관 담당자가 지정합니다. 기본 상태에서는 미리보기만 사용할 수 있습니다. 아래 예시의 주소와 서버를 실제 도서관 계정의 SMTP 설정으로 바꿔 배포 환경 변수에 등록합니다. 인증 정보는 저장소에 커밋하지 않습니다.

```dotenv
OVERDUE_EMAIL_ENABLED=false
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.org
EMAIL_PORT=587
EMAIL_HOST_USER=library@example.org
EMAIL_HOST_PASSWORD=메일_서비스에서_발급한_인증정보
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_TIMEOUT=10
DEFAULT_FROM_EMAIL="Österreichische Bibliothek HUFS <library@example.org>"
LIBRARY_CONTACT_EMAIL=library@example.org
```

`LIBRARY_CONTACT_EMAIL`은 본문의 문의 주소이자 Reply-To 주소입니다. 설정 후 발송 준비가 되면 `OVERDUE_EMAIL_ENABLED=true`로 변경합니다. 서비스에서 SSL 연결을 요구하면 해당 포트와 `EMAIL_USE_SSL=true`, `EMAIL_USE_TLS=false`를 사용합니다. TLS와 SSL을 동시에 켜지 않습니다. 실제 서버·포트·인증 방식은 선택한 메일 서비스의 안내를 따릅니다.

배포 시 `python manage.py migrate`로 발송 기록 테이블을 생성해야 합니다. 기존 Render 빌드 명령에는 이 단계가 포함되어 있습니다.

한 회원의 발송이 실패해도 다른 회원의 발송은 계속 진행하며, 결과를 나누어 표시합니다. **처리 중 / 결과 미확인** 또는 **발송 미완료 / 결과 확인 필요**가 표시되면 메일 서비스의 발송 내역도 확인한 후 재발송 여부를 결정합니다. 통신 중 연결이 끊겼을 때에는 실제 메일 접수 여부를 확정할 수 없습니다. **발송 완료**는 메일 서버 접수를 의미하며 수신함 도착을 보증하지 않습니다.

한 번의 요청에서는 메일 서버 연결을 재사용하며, 시작 후 10초가 지나면 다음 회원의 발송을 시작하지 않습니다. SMTP 연결의 개별 통신 대기 시간은 최대 5초로 제한합니다. 처리 시간 제한으로 시작하지 못한 인원은 별도로 표시하므로, 발송 기록을 확인한 뒤 해당 회원을 다시 선택해 진행합니다. 이미 시작한 메일 통신을 중간에 취소하는 제한은 아닙니다.

이 기능은 관리자가 실행하는 수동 발송만 제공합니다. 개발 테스트는 메모리 메일함을 사용하며 실제 수신자에게 메일을 보내지 않습니다.

## 한국어 예시

제목: **[한국외국어대학교 오스트리아 도서관] 대출 도서 반납 일정 확인 부탁드립니다**

> 김도서 님께,
>
> 안녕하세요. 한국외국어대학교 오스트리아 도서관입니다.
> 평소 저희 도서관을 이용해 주셔서 진심으로 감사드립니다.
>
> 현재 도서관 대출 기록상 아래 도서의 반납 예정일이 지난 것으로 확인되어, 조심스럽게 안내 말씀을 드립니다.
>
> - 도서명: Die Verwandlung
> - 청구기호: 예시-001
> - 반납 예정일: 2026-10-30 (예정일로부터 3일 경과)
>
> 바쁘시겠지만 위 도서의 반납 일정을 확인하시어 도서관으로 반납해 주시면 대단히 감사하겠습니다.
> 도서를 계속 이용하셔야 하거나 방문이 어려우신 경우에는 아래 연락처로 말씀해 주시기 바랍니다. 대출 기간 연장 가능 여부와 반납 방법을 함께 확인하여 안내해 드리겠습니다.
>
> 이미 반납해 주셨다면 전산 기록 반영 시점의 차이로 안내가 발송되었을 수 있습니다. 이 경우 너그러이 양해해 주시기 바라며, 확인이 필요하시면 언제든지 연락해 주시기 바랍니다.
>
> 귀한 시간 내어 확인해 주셔서 감사드립니다.
> 늘 건강하고 평안한 하루 보내시기를 바랍니다.
>
> 한국외국어대학교 오스트리아 도서관 드림
> 문의: [설정한 도서관 회신 주소]
> 전화: 02-2173-2283
> 위치: 한국외국어대학교 서울캠퍼스 본관 301호

전체 발송 템플릿: [overdue_ko.txt](../../backend/library/templates/library/emails/overdue_ko.txt)

## 독일어 예시

Betreff: **[Österreichische Bibliothek der HUFS] Freundliche Erinnerung an die Rückgabe Ihrer Bücher**

> Guten Tag Kim Doseo,
>
> wir danken Ihnen herzlich für die Nutzung der Österreichischen Bibliothek an der Hankuk University of Foreign Studies.
>
> Nach dem aktuellen Stand unserer Ausleihunterlagen ist die Leihfrist für die nachfolgend aufgeführten Bücher bereits abgelaufen. Daher möchten wir Sie höflich an die Rückgabe erinnern.
>
> - Titel: Die Verwandlung
> - Signatur: Beispiel-001
> - Rückgabedatum: 30.10.2026 (seit 3 Tagen überschritten)
>
> Wir wären Ihnen sehr verbunden, wenn Sie die Rückgabe dieser Bücher veranlassen könnten.
> Sollten Sie die Bücher weiterhin benötigen oder sollte Ihnen eine Rückgabe derzeit nicht möglich sein, setzen Sie sich bitte über die unten angegebenen Kontaktdaten mit uns in Verbindung. Gerne prüfen wir gemeinsam mit Ihnen, ob eine Verlängerung der Leihfrist oder eine andere Rückgabemöglichkeit in Betracht kommt.
>
> Falls Sie die Bücher bereits zurückgegeben haben, betrachten Sie diese Nachricht bitte als gegenstandslos. Möglicherweise wurde die Rückgabe noch nicht in unseren Unterlagen erfasst. Für diese Überschneidung bitten wir Sie höflich um Entschuldigung. Bei Rückfragen stehen wir Ihnen selbstverständlich gerne zur Verfügung.
>
> Für Ihre Zeit, Ihr Verständnis und Ihre Unterstützung danken wir Ihnen sehr herzlich.
> Wir wünschen Ihnen alles Gute und einen angenehmen Tag.
>
> Mit freundlichen Grüßen
> Ihre Österreichische Bibliothek
> Hankuk University of Foreign Studies
> E-Mail: [konfigurierte Kontaktadresse]
> Telefon: 02-2173-2283
> Standort: Hauptgebäude, Raum 301, Campus Seoul

전체 발송 템플릿: [overdue_de.txt](../../backend/library/templates/library/emails/overdue_de.txt)
