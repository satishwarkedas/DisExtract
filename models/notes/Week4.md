# Week 4 Report

## Plans

1. Training the why-question dataset
   - How to turn a statement (cause) into a question?
     - Erin provided a pattern, try it!!
2. Think about using A/B testing
   - Ask humans to distinguish between human reason vs. machine generated reason
   - Rank reasons for plausiblity

## TODO List

1. Run PGNet on the cluster, install everything

2. Generate new ReasonQA dataset

## ReasonQA

We first prep the Gigaword (116M) and NewsCrawl (191M) corpus in the format that matches DrQA Document Retriever's [format](https://github.com/facebookresearch/DrQA/tree/master/scripts/retriever). Since the original 300M dataset is rather large, we decide to collect only a fixed context! We find the `because` sentence pairs (that does not contain `because of`), and then use the 

So the reason we want a few paragraphs is not that the answer is `contained` in these paragraphs. The paragraphs are only providing `context`! Why questions are not as explicit in the paragraphs as other types of questions!

We choose the +/- 10 sentences when we first find `because` as the context. If two `because` appeared in the same context, the range will overlap.

We aim to create the largest distant supervision QA dataset to date for why question answering.

One nice thing we might be able to show is that **ReasonQA is perfect for pre-training PGNet type model, without DrQA** (rationale extraction). DrQA paper showed that PGNet drastically under-performed DrQA and DrQA + PGNet. This is perhaps the training set **100k** is too small.

So we get **32,812,353 (32.8M)** sentences as candidates for context! Then we build **DrQA document retriever** to pick the the candidate sentences. DrQA has a lot of filtering work. We only want some vague context. We don't care about exact retrieval.

**DrQA document retriever** will index everything and generate hash value for the bigrams. It fast-retrieves over millions of documents. We use it to match for S1 and S2 (it's ok that S1 and S2 are not exactly the same sentence as before. Also it's ok to retrieve more context/background than the original position of the sentence -- common knowledge / background / context can come from any relevant stories).



## Paper Summary

**A Semi-Supervised Learning Approach to Why-Question Answering**

(https://www.aaai.org/ocs/index.php/AAAI/AAAI16/paper/viewFile/12208/12056, 2016)



**Developing an approach for why-question answering**

(https://pdfs.semanticscholar.org/d431/7fba0a026d6bb957f2a48a981775ca9dc58f.pdf)



**DrQA: Reading Wikipedia to Answer Open-Domain Questions**

(https://arxiv.org/abs/1704.00051)

DrQA shows that through a bag of clever engineering tricks, we can scale up MR to MRS (Machine Reading at Scale).

Also, DrQA uses SQuAD to learn typed questions (what, where, when, who, etc.). Use it as base model, it can further be trained on other datasets using distant supervision (WikiMovie, CuratedTrec, etc.).

Each task can be thought of as giving the module/model/system an ability to do something (SQuAD --> answer different types of questions).

DrQA also creates distant supervision dataset using document retriever (something we can also do).

It's a nice training paradigm that should work on all retrieve -> read type of framework.

Distant supervision -> they find top 5 Wikipedia articles that contain relevant fact for datasets like WebQuestions and WikiMovies. Then since they have actual answer (short span), they find paragraphs that contain the answer, discard the rest.

**CoQA: A Conversational Question Answering Challenge**

(https://arxiv.org/pdf/1808.07042.pdf)

Nice dataset analysis section, including a section on **Linguistic Phenomenon** (lexical match, paraphrasing -- synonymy, actonymy, hyponymy and negation, pragmatics) 

(we can analyze our pairs collecting similar statistics)

**Models** section

First, co-attention or question-aligned paragraph encoding, etc., can be subsumed under the Transformer type of encoding (no need for explicit segmentation between question and answer).

Second, subsume extractive model under **Pointer-Generator network** (PGNet): p \<q\> q_{i-n} \<a\> a\_{i-n} ... (Just like the OpenAI paper.)


