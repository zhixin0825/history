#!/usr/bin/env python3
"""Validate the Hanshu chapter-001 split used by chronicle/hanshu-integration.

The repository working text marks chapters as *02-001*, *02-002*, ...
This checker deliberately verifies only segmentation and year-boundary sentinels;
it does not claim textual identity with the Zhonghua 2013 PDF.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "texts" / "02_hanshu_full.txt"

def chapter_001_paragraphs():
    text = TEXT.read_text(encoding="utf-8-sig")
    a = text.index("*02-001*") + len("*02-001*")
    b = text.index("*02-002*")
    return [x.strip() for x in text[a:b].splitlines() if x.strip()]

def main():
    p = chapter_001_paragraphs()
    assert len(p) == 115, len(p)
    sentinels = {
        1: "高祖，",
        9: "秦二世元年",
        12: "秦二年十月",
        19: "秦三年十月",
        23: "元年冬十月",
        34: "二年冬十月",
        44: "三年冬十月",
        53: "四年冬十月",
        60: "五年冬十月",
        79: "七年冬十月",
        83: "八年冬",
        86: "九年冬十月",
        90: "十年冬十月",
        93: "十一年冬",
        101: "十二年冬十月",
    }
    for n, prefix in sentinels.items():
        assert p[n-1].startswith(prefix), (n, p[n-1][:40])
    assert "六年冬十月" in p[71], p[71][:120]
    assert p[113].startswith("初，高祖不脩文學")
    assert p[114].startswith("贊曰")
    print("Hanshu *02-001*: 115 paragraphs; year sentinels OK")

if __name__ == "__main__":
    main()
