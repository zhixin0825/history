# Zinin-Xu-2020-CCDH：论文文字提取

CC BY-NC 4.0（ELRA/LREC2020专属声明）

论文PDF首页明示CC-BY-NC；LREC2020作者指南及ELRA会议出版主站明确版本为4.0。ACL通用页脚另称2016年后材料CC BY4.0，不据通用页脚覆盖ELRA专属声明，也不把论文许可自动外推到CCDH全部语料。

此文本由已保存PDF提取，未手改原文字；表格、字形和图版以同目录PDF原件为准。

<a id="page-1"></a>

## PDF第1页

```text
                                                    Proceedings of the 12th Conference on Language Resources and Evaluation (LREC 2020), pages 785–793
                                                                                                                              Marseille, 11–16 May 2020
                                                                           c European Language Resources Association (ELRA), licensed under CC-BY-NC




     Corpus of Chinese Dynastic Histories: Gender Analysis over Two Millennia

                                                   Sergey Zinin, Yang Xu
                            University of Massachusetts Amherst, University of Toronto
      Warring States Workshop, Amherst, Massachusetts, USA, Department of Computer Science, Toronto, Canada
                                szinin@research.umass.edu, yangxu@cs.toronto.edu

                                                               Abstract
                                                                                                                 rd
Chinese dynastic histories form a large continuous linguistic space of approximately 2000 years, from the 3 century BCE to the
18th century CE. The histories are documented in Classical (Literary) Chinese in a corpus of over 20 million characters, suitable for
the computational analysis of historical lexicon and semantic change. However, there is no freely available open-source corpus of
these histories, making Classical Chinese low-resource. This project introduces a new open-source corpus of twenty-four dynastic
histories covered by Creative Commons license. An original list of Classical Chinese gender-specific terms was developed as a case
study for analyzing the historical linguistic use of male and female terms. The study demonstrates considerable stability in the usage of
these terms, with dominance of male terms. Exploration of word meanings uses keyword analysis of focus corpora created for gender-
specific terms. This method yields meaningful semantic representations that can be used for future studies of diachronic semantics.

Keywords: Classical Chinese, dynastic histories, corpus linguistics, historical linguistics, semantics, gender, keyword analysis
                                                                       digitization of the dynastic histories 3 . However, despite
                    1.    Introduction                                 having been digitized and placed online, this resource is
                                                                       not available to the community at large. As Li et al.
The renowned sinologist Homer L. Dubs noted, “the                      (2012) wrote, “in recent years, the Academia Sinica has
world's greatest repository of historical information is to            constructed a corpus of Pre-Qin Chinese containing 20
be found in the twenty-five officially approved Chinese                classical literatures. However, this important resource
standard histories” (Dubs, 1946). This happened due to                 only supplies online queries, and has not been used to get
centrality of historiography toward the traditional Chinese            a statistical overview of the Pre-Qin vocabulary by the
culture. One result of this fact is the availability of a large        developers.” This is still true. Most researchers in the
resource for corpus linguistic studies of Classical Chinese.           Classical Chinese field do not provide access to the
Unlike many of the early Chinese literature, the Twenty-               corpora they worked on, and access to academic and
Four Dynastic Histories 1 have solid textological                      commercial resources is restricted or prohibited4. Only in
provenance; they were written under rigorous stylistic                 2014, Song and Xia (2014) presented free open-source
requirements in consistent Classical Chinese over a                    corpus of the Huainanzi—probably, the first such corpus
period of more than 2000 years (from the 3rd century BCE               available.
to the 18th century CE), making them one of the longest                There has been a recent growth in open linguistic
diachronic linguistic repositories.                                    diachronic resources, e.g., the HistWords project by W.L.
While some parts of these histories (e.g., chronicles benji)           Hamilton, J. Leskovec and D. Jurafsky (see HistWords).
are considered very formal, the main body of histories                 These authors note, that, in their existing resource,
consists of “biographies” (liezhuan). These biographical               “Chinese lacks sufficient historical data for this task, as
narratives present the life of Chinese society in different            only years 1950-1999 are usable” (Hamilton et al., 2016).
periods. Although philosophical treatises of the Warring               This project aims to improve the availability of open-
States and Early Imperial periods have invited research                source corpora of Classical Chinese by offering free
among computational linguists, few can compare with the                corpora that can be downloaded and used.
dynastic histories as a linguistic resource. The size of this          One source of digital Classical Chinese data is the
resource2 and its diachronic scope make it ideal for corpus            Chinese Wikisource (see Wikisource). The Wikisource
linguistic studies of Classical Chinese.
The significance of the Twenty-Four Histories as the                   3
major resource for computational linguistics has always                  “The original project began under the name “Computerization
been understood in the Chinese academy. The earliest and               of Historical Documents” in 1984 when researchers from both
one of the most authoritative online corpora of Classical              the Institute of History and Philology and the Computing Center
Chinese, the Academia Sinica’s Scripta Sinica (see                     at Academia Sinica worked together to key in the “Monographs
Scripta Sinica), was built on “Full Text Chinese                       on Economy” from the dynastic histories. In 1986, the project
documents” database project, which itself started as                   was expanded to include the entire twenty-five dynastic
                                                                       histories. In June 1990, the computerization of the full text of the
                                                                       dynastic histories was completed with the exception of the
1
  In the current project, the term Twenty-Four Histories is used,      charts.” This part of the project took six years and cost more
as it is more traditional. If the history of Qing dynasty, the         than NT$40,000,000 (approximately US$1,400,000). The
Qingshi, added, we could talk about the Twenty-Five Histories,         “database of the twenty-five dynastic histories” is the first and
as in the quotation from Dubs.                                         largest segment of the Full Text Project” (Lee and Chen, 1997).
2                                                                      4
  There are various estimates, depending on the source: over 20           For example, Li’s own project group that worked on Ancient
million tokens, by Dubs’ estimate (Dubs, 1946), or rather 39           Chinese Corpus (ACC) V1.0 since 2009 at the Nanjing Normal
million tokens (Lee and Chen, 1997), or 31 million tokens              University, as far as these authors found, only released one
(Huang and Wu). This project presents a corpus with over 23            classic (the Zuozhuan) on the commercial resource of LDC in
million characters (see Section 2).                                    2017.



                                                                    785
```

<a id="page-2"></a>

## PDF第2页

```text
contains the full text of the Twenty-Four Histories under           early Modern Chinese), and most of them are still present
the Creative Commons license, i.e., they could be freely            in Modern Chinese. Considering the novelty of this task,
used, re-distributed, and modified. However, there are two          the analysis of the usage of these terms has been limited
limitations: the philological provenance and the current            by the analysis of their context within the context
format. It should be noted that, unlike many other online           windows of sentence and paragraph structures. The idea
resources of Classical Chinese, the Wikisource is openly            was to try to establish the existence of special relations of
editable. The authors presume that the philological quality         certain context terms with male and female terms.
of Wikisource sources is sufficient for corpus analysis             Therefore, this study did not directly address the issue of
while challenging for exact textological studies. The other         semantic change. Rather it offered an initial exploration of
drawback is its online format. Copying the textual data,            the contextual (or semantic) environment of individual
cleaning them up, and reformatting take considerable                terms. A special focus sub-corpus of all sentences and
time. This project introduces the Corpus of Chinese                 paragraphs, where the term was entered, was created for
Dynastic Histories (CCDH, 2019), with a total of over 23            each term. Previous researchers have implemented this
million characters 5.                                               method of term semantic analysis — e.g., Lau and Cook
The authors hope that the CCDH corpus will alleviate the            (2012)—for the identification of novel senses of words.
lack of diachronic resources of Classical Chinese.                  However, Lau and Cook used topic modeling with Latent
Diachronic, or historical, linguistics has been developing          Dirichlet Allocation and Hierarchical Dirichlet Process
in the Western humanities since the 18th century because            (LDA/HDP) to extract senses of words. This method did
of growing availability of large diachronic digital corpora.
                                                                    not perform well in the current study of Classical Chinese
In particular, new computational linguistic methods have
been developed to analyze semantic change (see Tang,                corpus, where there is no word mark-up. Therefore, the
2018, for an up-to-date review).                                    keyword analysis (KA) method also has been
The dynastic histories contain a vast amount of                     implemented, and it has yielded meaningful results.
information on the traditional Chinese society and
Classical Chinese language, especially in liezhuan                                 2.    Corpus Description
(biographies) sections, which makes the bulk of the
corpus. This project focuses on the subject of gender               2.1.   Dynastic Histories in the Corpus
analysis of the dynastic histories. In modern linguistics,          The Chinese language has evolved in roughly three
Chinese language is generally considered “genderless,”              stages: Old Chinese, Medieval Chinese, and Modern
i.e., it lacks not only grammatical but also natural gender         Chinese (Norman, 1998). Classical Chinese could be
category (Stahlberg et al., 2007). Also, modern gender              considered as a written form of Old Chinese, which
analysis such as “gender classification” and “gender                formed in the past three centuries BCE (Dong, 2014). In
identification” are not applicable to the dynastic histories        post-Han period, it could be referred to as Literary
because they are all known to be written by men and from            Chinese. It is often perceived that Classical or Literary
a masculine discourse position.                                     Chinese practically has not changed since then, unlike
Farris (1988) is a pioneer in gender analysis of Modern             spoken language. Researchers agree that there should
Chinese, and her approach of studying gender through                have been some intercommunication between the current
covert and marked terms is still significant. Working in a
                                                                    spoken language and Classical Chinese, although this area
pre-digital age, she created the first lists of male and
                                                                    has not yet been considerably explored. The processed
female gendered terms (or gender-specific terms), and this
approach forms the basis of this study; gender-specific             text of histories, with dynastic periods and basic statistics,
terms of such categories as sex, kin, and official ranks            are presented in Table 1, and the Corpus of Chinese
were identified based on the vocabulary of the histories,           Dynastic Histories (CCDH) can be found at
and evidences of their semantic contexts were explored.             https://osf.io/tp729/.
Aside from Farris’ lists (created for Modern Chinese), the          2.2.   Corpus Creation and Composition
list of gender-specific terms created in this study for the
                                                                    The text of the twenty-four histories was taken from
dynastic histories is probably the first and largest of its
kind. It should be noted that it is not a comprehensive list        Wikisource and processed to remove all formatting,
of all such terms for every historical period. This study           except divisions by chapters (juan), paragraphs, and
                                                                    sentences. Although the text was already present online,
has been, from the beginning, a diachronic investigation,
                                                                    converting it into a corpus that could be used for various
and for over 2000 years, many terms, especially the
official ranks, which were introduced in the Shiji, were            Classical Chinese research required dedicated work,
                                                                    which makes this corpus a unique contribution. The
extinguished by the Mingshi time6. It was challenging to
create an exhaustive list of gender-specific terms, which           chapter numbers were entered in the form of *001* (for
are present in all dynastic histories, from the Shiji (period       juan 1) on a separate line. The text files, in UTF8 coding,
                                                                    could be found on the project GitHub site; they have
of Classical Chinese) to the Mingshi periods (period of
                                                                    names such as “01_shiji_full.txt” (for the Shiji)7.

5
  This confirms the conservative evaluation by Dubs (Dubs,
1946); however, with punctuation marks and white spaces the
volume of CCDH is over 27 million tokens, which is close to
                                                                    7
(Huang and Wu, 2018) evaluation (the latter study also includes       The description of file content of the OSF site is contained in
the large Qing dynasty history).                                    the README file on it. Specific file names will be omitted
6
  See Table 1 for the dynasties’ creation times.                    farther on.



                                                                  786
```

<a id="page-3"></a>

## PDF第3页

```text
These files were further parsed and processed to create        1,113,10,1,22,主
index files, where each character is placed on a separate
line in a related text file                                    means that this character is found in the History Number 1
                                                               (the Shiji), Chapter 113, 10th paragraph in this chapter,
                                                               first sentence in this paragraph, and 22nd position in the
 Name          Dynasty    Period     Chars       Types
                                                               sentence. All further experiments were conducted using
 Shiji         To Han     To 95         577256     5045        these index files, not the original text files.
                          bce
                                                                                  3.    Gender Terms
 Hanshu        Han        206 bce       773741     5906
                          – 24 ce                              Due to the inclusion of the “biographies” section, the
                                                               dynastic histories in the corpus contain not just purely
 Houhanshu     Houhan     25-220        690771     5553        historical data but also information on many aspects of
                                                               everyday life in China, including family stories, where
 Sanguozhi     Wei, Wu, 221-280         384155     4489        data on gender relations could be found. Therefore, it
               Shu                                             seems natural to do a gender analysis and consider what
                                                               information about gendered terms could be extracted.
 Jinshu        Jin        265-420      1149450     5794
                                                               As appeared in the bibliography collected by Marjorie
 Songshu       Liu-Song 420-479         800235     5825        Chan (see Chan), most linguistic gender studies of
                                                               Chinese could be classified through analysis of the history
 Nanqishu      Nan Qi     479-502       296729     4859        of pronouns, gender identification, and special women’s
                                                               language. There are limited studies of semantic gender
 Liangshu      Liang      502-557       293085     4915        analysis of Classical Chinese. One of the established
 Chenshu       Chen       557-589       163125     3970
                                                               methods of gender analysis used lists of gender-specific
                                                               terms (Crawford et al., 2004). As mentioned, Chinese is
 Weishu        Wei        386-550       965445     5325        genderless; therefore, it appears that the most appropriate
                                                               way to analyze gender in a Classical Chinese corpus is
 Beiqishu      Bei Qi     550-577       213172     3992        through semantic analysis of gender-specific words, i.e.,
                                                               such words that refer only to either males or females.
 Zhoushu       Zhou       535-581       260865     4136        Such words could be found among family, kinship, and
                                                               professional terms. Farris (1988) created several similar
 Suishu        Sui        581-618       693690     5544        lists, but her lists are based on Modern Chinese. However,
                                                               gender terms in Modern Chinese cannot form the
 Nanshi        Nan chao 420-589         675661     5160        immediate basis of investigation into a corpus of Classical
                                                               Chinese because of language change. Creating such a
 Beishi        Bei chao   386-618      1103684     5515        gender-specific list of terms for Classical Chinese is itself
                                                               challenging. Even more challenging is that such a list
 Jiutangshu    Tang       618-906      1984156     6382        should be applicable to a diachronic corpus of almost 2-
                                                               millennia scale, as official titles (an equivalent of
 Xintangshu    Tang       618-907      1769453     6838        occupational terms for dynastic histories), male and
                                                               female, often do not last longer than one or two
 Jiuwudaishi   Wu dai     907-960       605041     4661        dynasties8. To tackle this issue, the authors have identified
                                                               (via unigrams, bigrams, and trigrams) potential words that
 Xinwudaishi   Wu dai     907-960       290748     3922        should be on the list and are present in most critical
                                                               histories in the current corpus and extract their dictionary
 Songshi       Song       960-1279     3995199    11254
                                                               values, using CC-CEDICT dictionary project 9. The entries
                                                               on the gender-specific list include full character form,
 Liaoshi       Liao       907-1125      300866     3994        simplified form, pinyin Romanization, and English
                                                               translations by CC-CEDICT. See a sample in Table 2.
 Jinshi        Jin        1115-         940129     5102        There are 81 male and 31 female terms 10. The difference
                          1234                                 in numbers was caused by 1) the nature of historical
 Yuanshi       Yuan       1271-        1591729     5744
                                                               8
                          1368                                    Hucker’s indispensable dictionary of the official titles in
                                                               imperial China (Hucker, 1985) had been consulted in the process
 Mingshi       Ming       1368-        2828640     7407        of this work; however, it could not offer a ready-made solution.
                          1644                                 9
                                                                  CC-CEDICT dictionary, which is used by many Chinese
                                                               language-related projects, e.g., by UNIHAN database, is also
 Total                                23347014    15071        covered by Creative Commons license and therefore has been
                                                               used to provide translations in this project (see CC-CEDICT,
   Table 1: Text statistics for the twenty-four dynastic       UNIHAN).
                                                               10
     histories (length in characters with punctuations            The full list of the terms is available on the project site. The
                         removed).                             list of words that are present in all twenty-four histories would
and is provided with history, chapter, paragraph, sentence     have been much shorter; therefore, the current list is a
numbers, and position in the sentence, e.g., a line like:      compromise between the full list of gender-specific terms in all



                                                             787
```

<a id="page-4"></a>

## PDF第4页

```text
source, where there are more male actors, and 2) more                the context terms, a minimum of 10 entries for the corpus
developed nomenclature of male official titles in the                and a minimum of 5 target terms, stop-words included,
dynastic histories. Although male terms dominate female              there are about 6700 sentence-based context terms and
terms in the curated list, it is the largest gender list for         9400 paragraph-based context terms 13 . Several
Classical Chinese and serves as a basis for future work.             observations can be made:
                                                                          a) Many context terms are shared by male and
 女         女        nǚ        female; woman; daughter                          female gender-specific terms. Most context
 妻         妻        qī        wife                                             words of female terms are shared with male
 妇         婦        fù        woman; old variant of 妇                          terms. And even though there are many more
                                                                               male terms, a small number of them do not have
                                                                               any shared context terms with female terms. For
  Table 2: Sample lines from the gender-specific terms.                        sentences, there are only about 600 (or about
                                                                               10% context terms), and those terms are
                   4.    Methodology                                           comparatively rare characters, with rarely more
This work focuses on a simple approach among many                              than 30 entries in the entire corpus.
                                                                          b) An analysis of matrix supports grouping target
possible ways of performing gender analysis. One way of
studying would be to create word vectors, based on                             terms according to their distributional features.
                                                                               There are a few words in the target terms that
counting words in a close context of a term and then
comparing these vectors and establishing similarity                            could co-occur with at least 80% of context
                                                                               terms, e.g., 女, 母, 妻, 婦 in female terms and 王,
between gender terms. However, comparing the
                                                                               子, 公, 侯, 君, 臣, 兵, 帝, 士, 父, 孫 in male
similarities of gender-specific terms or even groups of
                                                                               terms. These terms could be called “star terms”
them was not included in the goals of this study. Rather,
this study is aimed at exploring linguistic context of the                     because they are “connected” to most of the
                                                                               context terms, as well as between themselves (as
two groups (male and female) of gender-specific terms. It
                                                                               shown later). Then, there are middle-range terms,
does so by creating joint context vocabulary for all terms
                                                                               which are connected to about 50% of the context
and a co-occurrence matrix (called “the synoptic co-
                                                                               terms, and, finally, there are low-connected
occurrence matrix” 11 ), where the target terms are the
                                                                               terms.
columns and the context terms are the rows, and synoptic
                                                                          c) About 8% of the context terms are connected to
word vectors could be considered as the columns.
                                                                               over 95 target terms for sentences and more than
This study regards textual and syntactical units, such as
                                                                               2000 such terms (around 20%) for paragraphs 14.
sentences and paragraphs (passages), as the two basic
                                                                               Therefore, at the paragraph level, there is a large
units of analysis. The semantic scopes of these syntactic
and textual structures are different. It could be expected                     group of characters that could be in the same
                                                                               context for male and female terms.
that the context terms for sentences (that are not common
                                                                     It is straightforward to see why context characters for
and functional words) are related to collocation and the
                                                                     male and female terms overlap considerably, especially
general structure of the meaning of the target terms. The
                                                                     for paragraphs. For most paragraphs, where there is at
context terms for paragraphs would be wider in semantic
                                                                     least one female term, there is also at least one male term
scope since they may describe a discourse topic.
                                                                     (this is also true for sentences, but in a lesser degree). Of
This study also explores semantic analysis of individual
                                                                     more than 280000 paragraphs in the corpus 15 , 31079
terms by focusing on context terms of the gender terms.
                                                                     contain at least one female term, and 172909 contain at
The authors extract “focus corpora” for a given term, from
                                                                     least one male term; 29371 paragraphs contain at least one
all sentences where this term is present 12 . Then, the
                                                                     male and one female terms, so the number of paragraphs
meaning of the term is explored under both topic model
and keyword analysis.                                                containing female terms and not having male terms is
                                                                     about 5.5%, i.e., if a paragraph topic includes a female
                                                                     actor (designated by gender-specific term, e.g., “wife”),
           5.    Experiments and Results                             there will almost always be a male actor (e.g., “husband”).
5.1.   Evidence for Synoptic Context of the                          However, if a paragraph contains some male terms, e.g.,
       Gender-Specific Target Terms                                  wang (king), it would often not contain any female terms.
The first experiment constructed a synoptic co-occurrence            It is thus not straightforward to establish differences
matrix of context terms of male and female terms in the              between male and female terms as groups using co-
                                                                     distributional words in this corpus. Female context terms
scope of sentences and paragraphs. The tables could be
considered count-based word vector table (columns are                would be subsumed by the male context terms. However,
                                                                     male terms have some semantic space free of female
vectors), where the vocabulary consists of context terms
                                                                     terms, i.e., topically, these paragraphs are not related to
of all gender-specific terms. The total number of all
context terms for all target terms in all histories is over
15000 (for sentences); however, with the cutoff values for

                                                                     13
histories, and the list of such terms that are present in all           See specific file names in the README file on the OSF
histories.                                                           project site.
11                                                                   14
   The term « synoptic» here used to underline simply that these        It should be noted that stop-words were not excluded from
context terms are collected for several or all target terms.         this table.
12                                                                   15
   Similar to Lau et al. (2012) and Cook et al. (2014).                 See data on the project site for statistics.




                                                                   788
```

<a id="page-5"></a>

## PDF第5页

```text
any family or other female-related matters16. This is one            It is noted that most pairs belong either to neutral or
of the forms in which male terms “dominate” female                   undefined type. To estimate the directionality of the
terms in the dynastic histories semantic space.                      remaining pairs, they are collected into respective
                                                                     diachronic normalized files on the project site. These files
5.2.   Evidence for Diachronic Change of Context                     contain 1955 pairs for paragraphs and 210 pairs for
       Terms of the Gender-Specific Target                           sentences.
       Terms                                                         The analysis of the diachronic change in context and
In the previous section, the study of context terms was              target terms co-occurrence reveals that a very small
conducted on the whole corpus, without diachronic                    portion of target–context word/character pairs exhibits
stratification. Having a diachronic corpus of such scale, it         considerable change. Most target–context co-occurrence
is logical to obtain evidence of diachronic changes in the           pairs are quite stable over 1500 years, which could be
context terms’ co-distribution with the target terms.                considered as a confirmation of existing, in classic
Additional files were created for this goal 17 . Each row            philology, thesis about grammatical and vocabulary
contains pairs of target terms with their context terms,             stability of Literary Chinese.
with absolute numbers for each dynastic history in
chronological succession. They only contain context terms            5.3.   Topic Modeling and Keyword Analysis of
that have more entries than the cutoff value (four, in this                 Gender-Specific Target Terms
case) at least for one dynasty. The files with normalized            The final experiment was a semantic analysis of
numbers contain the same pairs, but with normalized                  individual target terms. Two methods have been applied
numbers (divided by the dynasty history size in                      to the corpus in this experiment. Both methods employ the
characters). Normalized data allow tracking change for a             “focus corpus” approach, where a focus corpus is created
context character, in combination with a specific target of          for each target term based on the passages (within the
determining whether its usage is on the rise or decline,             context window) where the target term is found19.
i.e., diachronic change in its usage with the context term.          The method of clustering passages of a target word to
Columns in these tables are similar to the “meaning                  enrich semantic context of a document has been
vectors” used by Xu and Kemp (2015); however, in the                 popularized in word sense disambiguation/induction
current study, instead of measuring target vectors                   research since the beginning of this century20, in work by
divergence, the authors explored diachronic change of                Bordag (2006) (who suggested a sentence-length window)
usage of context terms. If for a specific target term, there         and then in work by Brody and Lapata (e.g., Brody and
are many context terms that are either on the rise or                Lapata, 2009), who, following Caj et al. (2007), used
decline, it may be an indication of a semantic change in             topic modeling.
the usage of the given target term.                                  Using topic modeling for identifying word senses through
The direction of change has been identified by linear                clustered contextual passages for target words was
regression, through normalized values of pairs’ entries, on          elaborated by Lau et al. (2012) and Cook et al. (2014),
the Y-axis and corpus documents in historical order of               who created focus corpora on the basis of three-sentence
writing on the X-axis. The distance between sources is               context window, where a target term appears in the
uniform (there is no presumption about the character of              middle sentence. They conducted a topic analysis, using a
temporal change of Classical Chinese, but it definitely              hierarchical version (HDP) of Latent Dirichlet Allocation
would not be linear18).                                              (LDA), to detect novel senses. In their study (Cook et al.,
The slope of the linear regression line can indicate the             2014), they also implemented keyword analysis (KA) for
direction of change. In this study, +1.5 and −1.5 were               target terms but yielded only limited use. This study uses
accepted as criteria of change. Pairs that demonstrate               similar methods, namely, latent semantic based topic
slopes more than 1.5 are considered to be on the rise (it            analysis (LSI), which resembles LDA and HDP) and
will be marked as up); pairs that have slope less than −1.5          KA21.
are considered to be on the decline (it will be marked as            The approach was to apply topic-based analysis (Blei et
down). The pairs, which have slope in between −1.5 and               al., 2003) to a focus corpus, consisting of one-sentence
−1 and 1 and 1.5, are considered to be of “undefined”                passages that contain the target characters 22 . As an
type. The pairs with slope in the interval of −0.5 and +0.5          illustration, two representative gendered words from the
are considered to be “neutral,” i.e., no definitive change.          gender list were chosen: nan (man) and nv (woman). The
The results for paragraphs and sentences are presented in            focus corpora for these words (based on one sentence
diachronic normalized files in the form described above              passage) have been created, and LDA and KA have been
(the normalized values of pairs’ entries are multiplied by
factor of 100000 and rounded). There are 250676 lines for            19
                                                                        These passages are considered to be “documents’ of the
paragraphs and 102145 lines for sentences.                           corpus.
                                                                     20
                                                                        This method of aggregating short passages for topic modelling
                                                                     is also not unlike the methods of topic modelling, applied for
16
   For example, the topic of a paragraph could be an activity of     study of Twitter, etc., corpora. See Hong and Davidson (2010).
                                                                     21
the king (wang), and this activity will not include any female          Following the standard methods described by Baron et al.,
actors.                                                              (2009) and Scott (2010).
17                                                                   22
   See specific file names in the README file on the OSF                Cook et al. use three-sentence passages for creating a focus
project site.                                                        corpus. This is a length in between average paragraphs and
18
   It would rather be expected to be synchronous with spoken         sentences in their study. However, considering the conciseness
Chinese evolution, which is not linear. However, the evolution       of classical Chinese, one sentence in this language could be
of Classical Chinese is not a well-researched area.                  longer in English.



                                                                   789
```

<a id="page-6"></a>

## PDF第6页

```text
applied to them23. The raw output for a run of the program                 study considers only two main measures: log-likelihood
for five topics for LDA is presented in the Table 3.                       (LL or G2) and chi-square (CHI2 or just CHI). Depending
Many topic characters appear in the topics, and topics are,                on the measure of keyness, keyword scores may be
actually, very close24. Because this study is less concerned               positive and negative. Positive keywords can be defined
with specific senses of a word and more concerned with                     as “comparatively overused” words in comparison with
meaning in its generality, topic characters were merged                    word use in the reference corpus, and negative keywords
(see Table 4) and redundant characters were removed.                       would be “comparatively underused.”
Although the result still contains “noise characters” it                   The main reason for analyzing corpus documents using
could be considered an aggregate of senses of the target                   keywords is the presumption that they express
characters. The merged results are shown in the Table 4                    “aboutness,” i.e., they allow understanding of content,
(sorted alphabetically).                                                   based on automatic extraction of frequent words 26.
The topic modeling correctly identifies the historical
characters of the document (official titles, names of                          Topics for nan (man)     Topics for nv (woman)
kingdoms) and includes some gender-specific terms (see
Table 3). For nan character, some topic characters
describe societal and political roles of a man (wang                           人 rén man                氏 shì clan name
(king), gong (Duke), guo (state), xiao (filial piety); others                  侯 hóu title              人 rén man
relate to his familial role (nv (woman), fu (father)). For nv                  兒 ér child               令 líng command
character, there are many related male terms (as women’s                       公 gōng title gong        公 gōng Duke
stories are mainly related to their male partners’                             取 qu take                別 bié to separate
biographies), such as di (emperor), wang (king), hou                           后 hòu empress            制 zhì to regulate
(marquis), gong (duke), jun (ruler) – even more so than                        大 dà big                 后 hòu empress
for nan. There are also a few female gender-specific                           太 tài greatest           國 guo state
terms, like hou (empress), mu (mother), qi (wife).                             婦 fù woman               城 chéng city
                                                                               子 zǐ son                 太 tài greatest
                                                                               母 mǔ mother              夫 fū husband
      LDA topics for nv             LDA topics for nan
                                                                               氏 shì clan name          女 nǚ woman
                                                                               為 wèi do                 子 zǐ son
      子為人王太生后大長氏                    氏 子 令人 日王 年 城楚 太                           無 wú not to have 王       帝 dì emperor
      為子后太王男人侯生大                    為 子 人女 長王 太 公帝 楚                           wàng king                年 nian year
      王為秦子公無取太婦人                    生子人為王女夫后幸                                  生 shēng give birth       幸 xìng fortunate
      為公人魯子生兒齊無王                    女 生 子無 制為 人 衛梁 禮                           男 nán man (male)         日 rì day
      子為王公秦母婦太齊無                    女子人王無國霸長別足                                 秦 qín state Qin          梁 liáng state Liang
                                                                               長 cháng grow             楚 chu state Chu
                                                                               魯 lǔ state Lu            為 wèi do
     Table 3: Topics retrieved from the focus corpus of nv                     齊 qí state Qi            無 wú not to have
                   (woman) and nan (man).                                                               王 wàng king
                                                                                                        生 shēng give birth
An alternative analysis was performed using KA method.                                                  禮 li ritual
Keyword analysis is a popular modern method of content                                                  衛 wèi guard
analysis of corpora. It is rooted in Firth (1957) and                                                   足 zú foot
Williams (2014) and introduced by Mike Scott in his                                                     長 chang grow
WordSmith software package 25 . KA involves the                                                         霸 bà feudal chief
comparison of word frequencies in a focus corpus and a
reference corpus. As such, “keywords are those whose
frequency (or infrequency) in a document or corpus is                          Table 4: Merged LDA sentence topic characters for nan
statistically significant, when compared to the standards                                           and nv.
set by a reference corpus” (Bondi, 2010). The significance
of a word as a potential keyword in the KA is measured                     The log-likelihood score (LL or G2) in this study was
by its “keyness score.”                                                    calculated following the formula, suggested by Paul
There are various measures of keyness in the                               Rayson (see Rayson in Resources):
implementation keyword extraction and ranking. This
                                                                                      G2 = 2*((a*ln (a/E1)) + (b*ln (b/E2)))27
23
   For all methods, the standard Python Gensim library was
                                                                           26
used; most stop-characters taken out (but not the target words),                 Hutchins     discerned    between     document’s    topic,
minimum frequency for terms was five. In the paper, only LDA               summarization, and aboutness, where “concept of 'aboutness' …
results are presented. For all results, see top topic characters files     associates the subject of a document not with some 'summary' of
on the project site.                                                       its total content but with the 'presupposed knowledge' of its
24
   It is not surprising, considering that most “female” segments           text.” (Hutchins, 1978)
                                                                           27
are also “male” segments, as they contain terms of both genders.              Where “a” is the frequency of a character in Corpus 1
Still, different senses could be extracted from each topic                 (Reference corpus), and “b” is the frequency of a character in
sequence, if necessary.                                                    Corpus 2 (corpus under testing); “c” is the number of characters
25
   See (Scott, 2010) for a modern version of it.                           in Corpus 1 and “d” is the number of characters in Corpus 2.



                                                                         790
```

<a id="page-7"></a>

## PDF第7页

```text
                                                                     projecting gender character of the term in question
                        Corp. 1    Corp. 2     Total                 automatically.

    Freq. of feature    a          b           a+b
                                                                           Nan (man)               Nv (woman)
    Freq. of feature    c          d           c+d
    not occurring                                                          男 nán man               主 zhǔ master
                                                                           伯 bo title bo           人 rén man
    Total               a+c        b+d         N=a+b+c+d                   夫 fū husband            公 gōng duke
                                                                           女 nǚ woman              后 hòu empress
                                                                           妤 yú fair               女 nǚ woman
       Table 5: Contingency table for the CHI2 test                        妻 qī wife               妃 fēi concubine
                                                                           姬 jī concubine          妓 jì prostitute
There are definitely more characters, related to gender                    婕 jié handsome          妹 mèi younger sister
context in the KA list. For instance, in the list for nv                   婚 hūn marry             妻 qī wife
(woman), there are such terms as fei (concubine), ji                       婦 fù woman              妾 qiè concubine
(prostitute), qi (wife), qie (concubine), fu (woman), and                  嫁 jià marry             姊 zǐ older sister;
some terms for marriage, that are not present in the topics.               子 zǐ son                娉 pīng graceful
CHI2 score for keywords was calculated using the                           孕 yùn pregnant          娶 qǔ marry
contingency table and the formula from (Baron et al.                       封 fēng title            婚 hūn marry
2009), see Table 5.                                                        戶 hù household          婦 fù woman;
                                                                           爵 jué vessel            婢 bi maid
         X2 = N(ad-bc)2/(a+b)(c+d)(a+c)(b+d)                               王 wàng king             壻 xù son-in-law
                                                                           生 shēng life            媧 Was surname Wa
Similar to the topic analysis, focus corpora were created                  產 chǎn to give birth    嫁 jià marry
for target words based on one-sentence context windows                     癃 lóng infirmity        嬪 pín imperial concubine
(these sentences were removed from the main corpus,                        笄 jī hairpin            子 zǐ son
which became the reference corpus). The results of the                     級 jí rank               州 zhou province
output (alphabetically sorted top thirty characters) are                   縣 xiàn county           母 mǔ mother;
presented in Table 6.                                                      袋 dài bag               氏 shì clan name
Table 7 summarizes a comparison between topic                              裸 luǒ naked             淫 yín excess
modeling and keyword analysis. Although there are some                     賜 cì bestow             男 nán man
overlapping terms in LDA and KA CHI2 lists (e.g., wang                     邑 yì city               直 zhí straight
(king)), there are more differences. Not only there are                    陽 yáng positive         織 zhī weave
more terms in the KA output that are found on the gender-                  髽 zhuā dress for hair   適 kuò proper
specific list, but there is also better fit from the KA to the             鰥 guān widower          駙 fù prince-consort
term’s semantics. For example, for woman, on the LDA
list, only three terms are from female gender-specific
group, while on the KA list there are nine such terms. The               Table 6: Top 30 keyword analysis (CHI2) characters for
KA list of terms offers a better description of women’s                                nan (man) and nv (woman).
roles in the traditional Chinese society, while the LDA list
instead indicates historical actors to whom women are                           6.     Discussion and Conclusion
attached.
                                                                     This study contributes to the community the new corpus
It should be recalled, that, from the beginning, topic
                                                                     of Classical Chinese (CCDH), on the basis of open-source
modeling was not about the “content” of the corpus. If the
                                                                     dynastic histories, covered by Creative Commons license.
focus corpus for nv could be defined as consisting of
                                                                     The datasets are free for downloading and refined
historical passages about women, then topic modeling
could be described as extracting its “historical topicality”,        processing (e.g., POS marking) by the public. This corpus
                                                                     is unique in that it supports both synchronic and
while KA method, in agreement with how it is defined by
                                                                     diachronic studies of Classical Chinese, where there is a
its developer, is rather extracting this “aboutness”, i.e., the
                                                                     dearth of free available and licensed corpora28.
content of the document.
                                                                     The second contribution of the study is to offer a case
The words, obtained through keyword analysis of focus
                                                                     study of how this corpus could be used, in terms of gender
corpora, can be useful for creating a semantic framework
                                                                     analysis. Gender analysis is not yet a developed area of
(or a template) of the meaning of the term, i.e., keyword
                                                                     research in Classical Chinese, so the authors had to create
analysis of the focus corpora can be useful for the
                                                                     a novel list of gender-specific terms. The study creates a
automatic creation of meaning templates for terms. The
                                                                     co-occurrence matrix of target terms from the gender-
list of gender-specific terms can be used as a criterion for
                                                                     specific list and their context terms. The list of context
                                                                     terms (“synoptic vocabulary”) underlines contextual
“a+b” will be the total number of a character in both corpora,
                                                                     28
and “c+d” is the number of all characters in both corpora. In           As mentioned above, another corpus that could be freely
these terms, expected values E1 (for Corpus 1) and E2 (for           downloaded and used by researchers is the Huainanzi, released
Corpus 2) will be E1 = c*(a+b) /(c+d) and E2 = d*(a+b)] / (c+d).     in 2014.



                                                                   791
```

<a id="page-8"></a>

## PDF第8页

```text
relations to the target terms. It is found that most target      Brody, S. and Lapata. M. (2009). Bayesian word sense
terms share context, but the male terms have larger                induction. In Proceedings of the Eleventh Conference of
synoptic vocabularies (i.e., more diverse context).                the European Chapter of the Association for
                                                                   Computational Linguistics (EACL’09), pages 103–111,
                                                                   Athens, Greece, march. The European Chapter of the
  LDA nan KA nan           LDA nv      KA nv                       Association for Computational Linguistics (EACL).
                                                                 Carlitz, K. (1991). The Social Uses of Female Virtue in
                                                                   Late Ming Editions of Lienu Zhuan. Late Imperial
  人 man       男 man        人 man       主 master                    China 12(2):117-148.
  侯 title     伯 title bo   公 Duke      人 man                     Cook, P., Lau, J.H., McCarthy, D. and Baldwin, T.
  兒 child     夫            后 empress   公 duke                      (2014). Novel word-sense identification. In Proceedings
  公 gōng      husband      夫 husband   后 empress                   of the 25th International Conference on Computational
  后 empress   女 woman      女 woman     女 woman                     Linguistics (COLING 2014): Technical Papers, pages
  婦 woman     妻 wife       子 son       妃 concubine                 1624–1635, Dublin, Ireland, august.
  子 son       姬            帝 emperor   妓 prostitute              Crawford, J., Leynes, P., Mayhorn, C. and Bink, M.
  母 mother    concubine    王 king      妹 sister                    (2004). Champagne, beer, or coffee? A corpus of
  王 king      婦 woman      霸 feudal    妻 wife                      gender-related and neutral words. Behavior Research
  男 man       子 son        chief       妾 concubine                 Methods, Instruments, & Computers, 36 (3): 444-458.
              王 king                   姊 older sister            Dubs, H.H. (1946). The Reliability of Chinese Histories.
              鰥                        婦 woman                     The Far Eastern Quarterly, 6(1): 23-43.
              widower                  婢 maid                    Dong, H. (2014). A History of the Chinese Language.
                                       壻 son-in-law                Routledge, Milton Park, Abingdon, Oxon, England.
                                       嬪 concubine               Farris, C.S. (1988). Gender and Grammar in Chinese:
                                       子 son                       With Implications for Language Universals. Modern
                                       母 mother                    China, 14 (3): 277-308.
                                       駙 consort                 Firth, J. R. (1957). A synopsis of linguistic theory, 1930-
                                                                   1955. In Studies in linguistic analysis (special volume
                                                                   of the Philological Society). Oxford: Blackwell, pp. 1-
Table 7: Comparison of LDA and KA terms, found on the              32.
             gender-specific list of terms.                      Hamilton, W.L., Leskovec, J. and Jurafsky, D. (2016).
                                                                   Diachronic Word Embeddings Reveal Statistical Laws
The diachronic analysis of context terms in the synoptic           of Semantic Change. In Proceedings of the 54th Annual
vocabularies reveals that these vocabularies are relatively        Meeting of the Association for Computational
stable, i.e., not many pairs of context-target terms display       Linguistics (Volume 1: Long Papers) pages 1489–1501,
substantial change (or considerable increase and decrease          Berlin, Germany, august.
in frequency over time). This study opens up opportunities       Hong, L. and Davison, B. (2010). Empirical Study of
for future inquiries into semantic change and the historical       Topic Modeling in Twitter. In Proceedings of the First
lexicon in Classical Chinese.                                      Workshop on Social Media Analytics (SOMA ’10),
                                                                   pages 80-88, Washington, DC, USA, july.
              7.    Acknowledgements                             Huang S. and Wu, J. (2018). A Pragmatic Approach for
                                                                   Classical Chinese Word Segmentation. In Proceedings
We would like to thank the anonymous reviewers and Ella
                                                                   of the Eleventh International Conference on Language
Rabinovich for their helpful comments and suggestions.
                                                                   Resources and Evaluation (LREC’18), pages 1161-
                                                                   1168, Miyazaki, Japan, may. European Language
         8.    Bibliographical References                          Resource Association (ELRA).
Baron, A., Rayson, P. and Archer, D. (2009). Word                Hucker, C. (1985). A Dictionary of Official Titles in
  Frequency and Key Word Statistics in Corpus                      Imperial China. Stanford: Stanford University Press.
  Linguistics. Anglistik: International Journal of English       Hutchins, W. J. (1978). The Concept of ‘Aboutness’ in
  Studies, 20(1):41–67.                                            Subject Indexing. Aslib Proceedings, 30(5):172-181.
Blei, D. M., Ng, A. Y., and Jordan, M. I. (2003). Latent         Lau J.H., Cook, P., McCarthy, D., Newman, D. and
  Dirichlet allocation. Journal of Machine Learning                Baldwin, T. (2012). Word sense induction for novel
  Research, 3:993–1022.                                            sense detection. In Proceedings of the 13th Conference
Bondi, M. Perspectives on Keywords and Keyness: An                 of the European Chapter of the Association for
  Introduction. (2010). In Bondi, M. and Scott, M. (Eds.),         Computational Linguistics (EACL 2012), pages 591–
  Keyness in Texts. Studies in Corpus Linguistics, 41.             601. Avignon, France, april.
  Amsterdam; Philadelphia: John Benjamins Pub. Co,               Li, B., Xi, N., Feng, M, and Chen, X. (2012). Corpus-
  pp.1–18.                                                         Based Statistics of Pre-Qin Chinese. In Donghong Ji
Bordag, S. (2006). Word sense induction: Triplet-based             and Guozheng Xiao, editors, Chinese Lexical
  clustering and automatic evaluation. In Proceedings of           Semantics: 13th Workshop, CLSW 2012, Revised
  the Eleventh Conference of the European Chapter of the           Selected Papers, pages 145-153, Wuhan, China, july,
  Association for Computational Linguistics (EACL’06),           Lee, J and Chen, J-S. (1997). The "Database of Full Text
  pages 137–144, Trento, Italy, april. The European                Chinese Documents" at the Institute of History and
  Chapter of the Association for Computational                     Philology, Academia Sinica. In Conference Materials
  Linguistics (EACL).                                              for Pacific Neighborhood Consortium 1997 Special



                                                               792
```

<a id="page-9"></a>

## PDF第9页

```text
  Meeting                      in                  Taipei
  (http://pnclink.org/publications/1997.htm).
Norman, Jerry (1998). Chinese. Cambridge University
  Press, Cambridge.
Scott, M. (2010). WordSmith Tools Version 5. Lexical
  Analysis Software, Liverpool.
Song, Y and Xia, F. (2014). Modern Chinese Helps
  Archaic Chinese Processing: Finding and Exploiting the
  Shared Properties. In Proceedings of the 9th
  International Conference on Language Resources and
  Evaluation (LREC’14), pages 3129-3126, Reykjavik,
  Iceland,     may. European        Language Resource
  Association (ELRA).
Stahlberg, D., Braun, F., Irmen, L. and Sczesny, S.
  (2007). Representation of the sexes in language. In K.
  Fiedler (Ed.), (Series Editors: A. W. Kruglanski & J. P.
  Forgas), Social communication. A volume in the series
  Frontiers of Social Psychology, New York: Psychology
  Press. Social Communication, pp. 163-187.
Tang, X. (2018). A state-of-the-art of semantic change
  computation. Natural Language Engineering, 24(5):
  649-676.
Wilkinson, E. (2012). Chinese History: A New Manual.
  Harvard University Asia Center, Cambridge, MA.
Williams, R. (2014). Keywords: A Vocabulary of Culture
  and Society. Oxford University Press, New York, New
  edition.
Xu, Y. and Kemp, C. (2015). A computational evaluation
  of two laws of semantic change. In Proceedings of the
  37th Annual Meeting of The Cognitive Science Society.
Zadrozny, W. and Jensew K. (1991). Semantics of
  Paragraphs. Computational Linguistics, 17(2): 171-209.

      9.   Language Resource References
Ancient Chinese Corpus (2017)
  https://catalog.ldc.upenn.edu/docs/LDC2017T14/
  https://catalog.ldc.upenn.edu/LDC2017T14
CC-CEDICT dictionary
  https://cc-cedict.org/wiki/
Chan, M. Chinese Language and Gender On-line
  Bibliography.
  http://people.cohums.ohio-state.edu/chan9/g-bib.htm
Corpus of Chinese Dynastic Histories (CCDH)
  https://osf.io/tp729/
HistWords,
  Word Embeddings for Historical Text by William L.
  Hamilton, Jure Leskovec, Dan Jurafsky
  https://nlp.stanford.edu/projects/histwords/
Scripta Sinica:
  http://hanchi.ihp.sinica.edu.tw/ihp/hanji.htm, Institute
  of History and Philology, Academia Sinica;
  http://applyonline.ihp.sinica.edu.tw/english/source/sour
  ce6.htm
The Huainanzi Corpus (2014)
  http://faculty.washington.edu/fxia/hnz/
Rayson, P. How to calculate log likelihood
  http://ucrel.lancs.ac.uk/llwizard.html
UNIHAN
  https://unicode.org/charts/unihansearch.html
Wikisource
  https://zh.wikisource.org/wiki/Template:%E4%BA%8C
  %E5%8D%81%E5%9B%9B%E5%8F%B2




                                                             793
```
