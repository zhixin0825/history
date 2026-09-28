# 二十四史全文 TXT

本仓库收录二十四史全文，共 24 个 UTF-8 TXT 文件。文本保持 Corpus of Chinese Dynastic Histories（CCDH）在 OSF 发布的原始字节，不进行繁简转换、断句重排或人工校改。

## 文件目录

| 编号 | 书名 | 文件 |
|---:|---|---|
| 01 | 史记 | `texts/01_shiji_full.txt` |
| 02 | 汉书 | `texts/02_hanshu_full.txt` |
| 03 | 后汉书 | `texts/03_houhanshu_full.txt` |
| 04 | 三国志 | `texts/04_sanguozhi_full.txt` |
| 05 | 晋书 | `texts/05_jinshu_full.txt` |
| 06 | 宋书 | `texts/06_songshu_full.txt` |
| 07 | 南齐书 | `texts/07_nanqi_full.txt` |
| 08 | 梁书 | `texts/08_liangshu_full.txt` |
| 09 | 陈书 | `texts/09_chenshu_full.txt` |
| 10 | 魏书 | `texts/10_weishu_full.txt` |
| 11 | 北齐书 | `texts/11_beiqishi_full.txt` |
| 12 | 周书 | `texts/12_zhoushu_full.txt` |
| 13 | 隋书 | `texts/13_suishu_full.txt` |
| 14 | 南史 | `texts/14_nanshi_full.txt` |
| 15 | 北史 | `texts/15_beishi_full.txt` |
| 16 | 旧唐书 | `texts/16_jiutangshu_full.txt` |
| 17 | 新唐书 | `texts/17_xintangshi_full.txt` |
| 18 | 旧五代史 | `texts/18_jiuwudaishi_full.txt` |
| 19 | 新五代史 | `texts/19_xinwudaishi_full.txt` |
| 20 | 宋史 | `texts/20_songshi_full.txt` |
| 21 | 辽史 | `texts/21_liaoshi_full.txt` |
| 22 | 金史 | `texts/22_jinshi_full.txt` |
| 23 | 元史 | `texts/23_yuanshi_full.txt` |
| 24 | 明史 | `texts/24_mingshi_full.txt` |

## 来源与引用

- 原始项目：[Chinese Dynastic Histories（OSF）](https://osf.io/tp729/)
- 论文：Sergey Zinin and Yang Xu, [Corpus of Chinese Dynastic Histories: Gender Analysis over Two Millennia](https://aclanthology.org/2020.lrec-1.98/), LREC 2020, pp. 785-793.
- CCDH 说明文本见 [`provenance/CCDH_README.txt`](provenance/CCDH_README.txt)。
- OSF 文件下载清单见 [`provenance/osf_manifest.json`](provenance/osf_manifest.json)。

论文说明，CCDH 的底本取自 Wikisource，语料采用 Creative Commons 许可，可使用、再分发和修改。OSF 项目元数据没有标明具体的 CC 许可版本；本仓库不对原始语料主张额外权利。研究或发表时请引用上述论文。

## 完整性

- 24 个文件合计 85,181,157 字节。
- 所有文件均可按 UTF-8 解码，无 NUL 字节。
- 文件保留原始 UTF-8 BOM 和换行，不由 Git 自动转换。
- [`SHA256SUMS.txt`](SHA256SUMS.txt) 可用于逐文件校验。

## 已知问题

OSF 原始文件中有 92 个 Unicode 替代字符 `U+FFFD`（`�`）。它们不是本仓库复制过程造成的乱码。为避免无依据地猜字，本仓库保持原文：

| 文件 | `U+FFFD` 数量 |
|---|---:|
| `02_hanshu_full.txt` | 3 |
| `03_houhanshu_full.txt` | 1 |
| `07_nanqi_full.txt` | 20 |
| `17_xintangshi_full.txt` | 21 |
| `20_songshi_full.txt` | 31 |
| `22_jinshi_full.txt` | 12 |
| `23_yuanshi_full.txt` | 1 |
| `24_mingshi_full.txt` | 3 |

这些文件适合语料分析和检索，但不应在未经版本校勘的情况下作为严格的点校本使用。
