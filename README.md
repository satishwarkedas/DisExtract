## Note

This is the official repo that we used to train for DisSent paper. It is not yet cleaned up and not ready for official release. But it has come to our notice that the community still lacks efficient sentence representation models (public ones), so we are providing access to people our trained model. 

You can download the trained models from the following AWS S3 link:
https://s3-us-west-2.amazonaws.com/dissent/ (Books 5, Books 8, and Books ALL)

You can also load the models by using the following script:
https://github.com/windweller/SentEval/blob/master/examples/dissent.py
https://github.com/windweller/SentEval/blob/master/examples/dissent_eval.py

Please contact anie@stanford.edu if you have problem using these scripts! Thank you!

We wrote the majority of the code in 2017 when PyTorch was still at version 0.1 and Python 2 was still popular. You might need to adjust your library versions in order to load in the model.

## DisSent Corpus

The links to data is available under the same link: 

https://s3-us-west-2.amazonaws.com/dissent/ (Books 5, Books 8, Books ALL, Books ALL -- perfectly balanced)

If you scroll down, beneath the trained model pickle files, you can find download links for all our data.

We include all the training files (with the original train/valid/test split). We do not provide access to the original raw BookCorpus data at all.

Once you install [AWS-CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) (commandline tool from AWS), you can download using commands like below:

```
aws s3 cp https://s3-us-west-2.amazonaws.com/dissent/data/discourse_EN_ALL_and_then_because_though_still_after_when_while_but_also_as_so_although_before_if_2017dec21_train.tsv .
```

## PDTB 2 Caveat

In the main portion of our paper, we stated that we "use the same dataset split scheme for this task as for the implicit vs explicit task discussed above. Following Ji and Eisenstein (2015) and Qin et al. (2017)". This line caused confusion. In terms of dataset split scheme, we followed "Patterson and Kehler (2013)’s preprocessing. The dataset contains 25 sections in total. We use sections 0 and 1 as the development set, **sections 23 and 24** for the **test set**, and we train on the remaining sections 2-22.". This is made clear in the Appendix Section A.3.

As far as we know, Ji and Eisenstein (2015) and Qin et al. (2017) both used **sections 21-22** as the test set. It appears that they weren't aware the existence of **sections 23 and 24** at the time. In order to move the field forward, we highly encourage you to follow Patterson and Kehler (2013) processing scheme and use https://github.com/cgpotts/pdtb2 to process.

The code to extract sections 23 and 24 is the following:

```python
from pdtb2 import CorpusReader

corpus = CorpusReader('pdtb2.csv')

test_sents = []

for sent in corpus.iter_data():
    if sent.Relation == 'Implicit' and sent.Section in ['23','24']:
        if len(sent.ConnHeadSemClass1.split('.')) != 1:
            test_sents.append(sent)
```

Patterson, Gary, and Andrew Kehler. "Predicting the presence of discourse connectives." Proceedings of the 2013 Conference on Empirical Methods in Natural Language Processing. 2013. [link](https://www.aclweb.org/anthology/D13-1094)


## Dependency Pattern Instructions

```python
depdency_patterns = [
    "still": [
        {"POS": "RB", "S2": "advmod", "S1": "parataxis", "acceptable_order": "S1 S2"},
        {"POS": "RB", "S2": "advmod", "S1": "dep", "acceptable_order": "S1 S2"},
    ],
    "for example": [
        {"POS": "NN", "S2": "nmod", "S1": "parataxis", "head": "example"}
    ],
    "but": [
        {"POS": "CC", "S2": "cc", "S1": "conj", "flip": True}
    ],
]
  
```

`Acceptable_order: "S1 S2""`: a flag to reject weird discourse term like "then" referring to previous sentence, 
but in itself a S2 S1 situation. In general it's hard to generate a valid (S1, S2) pair.

`flip: True`: a flag that means rather than S2 connecting to marker, S1 to S2; it's S1 connecting to marker, 
then S1 connects to S2.

`head: "example""`: for two words, which one is the one we use to match dependency patterns. 

## Parsing performance

Out of 176 Wikitext-103 examples:
* accuracy = 0.81 (how many correct pairs or rejections overall?)
* precision = 0.89 (given that the parser returns a pair, was that pair correct?)

This excludes all "still" examples, because they were terrible.
