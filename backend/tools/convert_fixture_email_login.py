"""학번 PK → 자동 id PK 전환용 fixture 변환 스크립트.

구 스키마에서 뽑은 dumpdata JSON 을 신 스키마(members.0005_email_login 이후)에서
loaddata 로 넣을 수 있는 형태로 바꾼다. 학번(sid)은 어디에도 남기지 않는다.

사용법:
    python tools/convert_fixture_email_login.py old_dump.json new_dump.json
"""
import argparse
import json
import sys

# 구 스키마에서 Member 의 pk(학번)를 참조하던 자리
MEMBER_REFS = {
    "manager.manager": ["__pk__"],
    "library.loan": ["member"],
}
# 구 스키마에서 Manager 의 pk(= Member 의 학번)를 참조하던 자리
MANAGER_REFS = {
    "library.book": ["registrar_manager", "modification_manager"],
    "library.loan": ["loan_manager"],
    "library.notice": ["manager"],
}
# 신 스키마에서 사라진 Member 필드
DROPPED_MEMBER_FIELDS = ["username"]


def build_id_map(objects):
    """구 Member pk(학번)를 1부터 시작하는 새 id 로 매핑한다."""
    sids = sorted(o["pk"] for o in objects if o["model"] == "members.member")
    return {sid: new_id for new_id, sid in enumerate(sids, start=1)}


def remap(objects, id_map):
    missing = []

    for obj in objects:
        model = obj["model"]
        fields = obj["fields"]

        if model == "members.member":
            obj["pk"] = id_map[obj["pk"]]
            for name in DROPPED_MEMBER_FIELDS:
                fields.pop(name, None)
            continue

        # Manager 의 pk 는 Member 를 가리키는 FK 이기도 하다.
        if model in MEMBER_REFS and "__pk__" in MEMBER_REFS[model]:
            if obj["pk"] not in id_map:
                missing.append((model, "pk", obj["pk"]))
            else:
                obj["pk"] = id_map[obj["pk"]]

        for name in MEMBER_REFS.get(model, []) + MANAGER_REFS.get(model, []):
            if name == "__pk__":
                continue
            old = fields.get(name)
            if old is None:
                continue
            if old not in id_map:
                missing.append((model, name, old))
            else:
                fields[name] = id_map[old]

    return missing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("dst")
    args = parser.parse_args()

    with open(args.src, encoding="utf-8") as f:
        objects = json.load(f)

    id_map = build_id_map(objects)
    if not id_map:
        sys.exit("members.member 객체가 없습니다. 덤프 대상을 확인하세요.")

    missing = remap(objects, id_map)
    if missing:
        for model, field, value in missing:
            print(f"  참조 불가: {model}.{field} -> {value}", file=sys.stderr)
        sys.exit(f"매핑되지 않은 회원 참조 {len(missing)}건. 중단합니다.")

    with open(args.dst, "w", encoding="utf-8") as f:
        json.dump(objects, f, ensure_ascii=False, indent=2)

    print(f"회원 {len(id_map)}명 재매핑, 총 {len(objects)}개 객체를 {args.dst} 에 기록했습니다.")


if __name__ == "__main__":
    main()
