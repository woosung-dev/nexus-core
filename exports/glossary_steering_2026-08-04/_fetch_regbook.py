# 규정집 2026 원본 PDF 회수 — R2 버킷에서 sha256 로 특정한다. 읽기 전용.
#
# admin/bots.py 는 Gemini 업로드 전에 원본을 R2 에 저장하지만 키를 uuid4().hex 로 랜덤화하고
# 매핑을 DB 에 남기지 않는다(문서 테이블 자체가 없음). 파일명으로는 못 찾는다.
# 대신 Gemini custom_metadata 의 content_sha256 으로 버킷을 대조한다 —
# 선행 세션이 용어집 PDF 를 이 방법으로 회수했다(_glossary_etl.py 주석).
#
# 목적: 회수 범위(청크 76개·64쪽) 밖에 축복자녀×축복자녀 축복 규정이 있는지 전량 확인.
import argparse
import hashlib
import logging
import sys
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
sys.path.insert(0, str(ROOT / "backend"))
for _n in ("botocore", "boto3", "urllib3", "s3transfer"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from app.services.storage.r2 import R2FileStorage  # noqa: E402

DIR = Path(__file__).parent
# 봇11 규정집 2026 — 선행 세션이 grounding custom_metadata 로 확인한 값
SHA_REG = "7cab18fd146cdcacfce2623f87da16a61fc241b1590fe7ca6eba445c6c8131fd"


def main(target_sha, out_name, max_mb):
    st = R2FileStorage()
    client, bucket = st._client, st._bucket

    keys, token = [], None
    while True:
        kw = {"Bucket": bucket, "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        r = client.list_objects_v2(**kw)
        keys += [(o["Key"], o["Size"]) for o in r.get("Contents", [])]
        if not r.get("IsTruncated"):
            break
        token = r.get("NextContinuationToken")

    pdfs = [(k, s) for k, s in keys if s <= max_mb * 1024 * 1024]
    pdfs.sort(key=lambda x: -x[1])
    print(f"버킷 '{bucket}' 객체 {len(keys)}개 · 후보 {len(pdfs)}개 (≤{max_mb}MB)")

    for i, (k, s) in enumerate(pdfs, 1):
        body = client.get_object(Bucket=bucket, Key=k)["Body"].read()
        sha = hashlib.sha256(body).hexdigest()
        if sha == target_sha:
            p = DIR / out_name
            p.write_bytes(body)
            print(f"[{i}/{len(pdfs)}] 일치 — key={k} {s/1e6:.1f}MB sha={sha[:16]}")
            print(f"→ {p}")
            return
        if i % 20 == 0:
            print(f"  …{i}/{len(pdfs)} 대조", flush=True)

    print(f"⚠ sha256={target_sha[:16]}… 와 일치하는 객체 없음 (후보 {len(pdfs)}개 전수 대조)")
    raise SystemExit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default=SHA_REG)
    ap.add_argument("--out", default="_src_규정집2026.pdf")
    ap.add_argument("--max-mb", type=int, default=60)
    a = ap.parse_args()
    main(a.sha, a.out, a.max_mb)
