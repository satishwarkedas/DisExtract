

import argparse
import sklearn.linear_model
import sklearn.feature_extraction
from collections import Counter
from sys import exit
import numpy as np
from scipy.sparse import coo_matrix, hstack

parser = argparse.ArgumentParser(description='Baselines')

parser.add_argument("--corpus", type=str, default='books_5', help="books_5|books_old_5|books_8|books_all|gw_5|gw_8")
parser.add_argument("--outputdir", type=str, default='sandbox/', help="Output directory")
parser.add_argument("--features", type=str, default="bow", help="arora|bow|avg|mostcommonclass")
parser.add_argument("--ndims", type=int, default=1000)
parser.add_argument("--min_count", type=int, default=3)
parser.add_argument("--run_through_subset", type=bool, default=False)


params, _ = parser.parse_known_args()
print(params)


def unigrams_phi(words):
	return Counter(words)

def bigrams_phi(words):
	return Counter([words[i-2:i] for i in range(len(words)) if i>1])

def trigrams_phi(words):
	return Counter([words[i-3:i] for i in range(len(words)) if i>3])

def unigrams(words):
	return words

def bigrams(words):
	return [" ".join(words[i-2:i]) for i in range(len(words)) if i>1]

def trigrams(words):
	return [" ".join(words[i-3:i]) for i in range(len(words)) if i>3]

def ngrams(sentence):
	words = sentence.split(" ")
	return trigrams(words) + bigrams(words) + unigrams(words)

def ngrams_phi(words):
	return Counter(trigrams(words) + bigrams(words) + unigrams(words))

def read_corpus(corpus_label):
	corpus_dir = "/home/anie/DisExtract/data/books/"
	labels = {
		"books_all": "discourse_EN_ALL_and_then_because_though_still_after_when_while_but_also_as_so_although_before_if_2017dec21_",
		"books_8": "discourse_EN_EIGHT_and_but_because_if_when_before_so_though_2017dec18_",
		"books_5": "discourse_EN_FIVE_and_but_because_if_when_2017dec12_"
	}
	corpus = {}
	for split in ["train", "valid", "test"]:
		filename = corpus_dir + labels[corpus_label] + split + ".tsv"
		print("reading {}".format(filename))
		corpus[split] = {"s1": [], "s2": [], "label": []}
		for line in open(filename):
			s1, s2, label = line[:-1].split("\t")
			corpus[split]["s1"].append(s1)
			corpus[split]["s2"].append(s2)
			corpus[split]["label"].append(label)
	return corpus

def get_most_common_class_accuracies():
	corpus = read_corpus(params.corpus)
	train_counter = Counter(corpus["train"]["label"])
	print(train_counter)
	test_counter = Counter(corpus["test"]["label"])
	print(test_counter)
	most_common_train_class = train_counter.most_common()[0][0]
	n_correct = test_counter[most_common_train_class]
	n_total = sum([test_counter[label] for label in test_counter])
	print(float(n_correct)/n_total)

def run_baseline_BoW_model(params):
	corpus = read_corpus(params.corpus)
	if params.run_through_subset:
		corpus["train"]["s1"] = corpus["train"]["s1"][:100]
		corpus["train"]["s2"] = corpus["train"]["s2"][:100]
		corpus["train"]["label"] = corpus["train"]["label"][:100]
		corpus["test"]["s1"] = corpus["test"]["s1"][:100]
		corpus["test"]["s2"] = corpus["test"]["s2"][:100]
		corpus["test"]["label"] = corpus["test"]["label"][:100]
	vectorizer = sklearn.feature_extraction.DictVectorizer()
	train_dicts_1 = []
	train_dicts_2 = []
	test_dicts_1 = []
	test_dicts_2 = []
	train_labels = []
	test_labels = []
	all_features = Counter([])
	print("collecting ngrams")
	for i in range(len(corpus["train"]["s1"])):
		s1 = corpus["train"]["s1"][i]
		s2 = corpus["train"]["s2"][i]
		features1 = ngrams(s1)
		features2 = ngrams(s2)
		all_features.update(features1 + features2)
		label = corpus["train"]["label"][i]
		train_labels.append(label)
		train_dicts_1.append(Counter(features1))
		train_dicts_2.append(Counter(features2))
		if i%100000==0:
			print("{}K of {}K in training set processed".format(round(i/1000), round(len(corpus["train"]["s1"])/1000)))
	for i in range(len(corpus["test"]["s1"])):
		s1 = corpus["test"]["s1"][i]
		s2 = corpus["test"]["s2"][i]
		features1 = ngrams(s1)
		features2 = ngrams(s2)
		all_features.update(features1 + features2)
		label = corpus["test"]["label"][i]
		test_labels.append(label)
		test_dicts_1.append(Counter(features1))
		test_dicts_2.append(Counter(features2))
		if i%100000==0:
			print("{}K of {}K in test set processed".format(round(i/1000), round(len(corpus["test"]["s1"])/1000)))
	all_dicts = train_dicts_1 + train_dicts_2 + test_dicts_1 + test_dicts_2
	support = [feature for feature in all_features if all_features[feature]>=3]
	print("vectorizing dataset")
	feat_matrix = vectorizer.fit(all_dicts)
	vectorizer.restrict(support)
	train1 = vectorizer.transform(train_dicts_1)
	train2 = vectorizer.transform(train_dicts_2)
	test1 = vectorizer.transform(test_dicts_1)
	test2 = vectorizer.transform(test_dicts_2)
	train_X = hstack([train1, train2]).toarray()
	test_X = hstack([test1, test2]).toarray()
	print(train_X.shape)
	print(train_X.shape)
	#print(type(train1))
	#train_X = np.concatenate((train1, train2), axis=0)
	#test_X = np.concatenate((test1, test2), axis=1)
	train_y = train_labels
	test_y = test_labels
	print("fitting model")
	model = sklearn.linear_model.LogisticRegression(max_iter=100, verbose=0, fit_intercept=True)
	model.fit(train_X, train_y)
	print("testing model")
	test_pred = model.predict(test_X)
	results = {label: {"hits": 0, "actual": 0.0000001, "predicted": 0.00000001} for label in set(train_y)}
	for i in range(len(test_y)):
		actual = test_y[i]
		predicted = test_pred[i]
		if actual==predicted:
			results[actual]["hits"] += 1
		results[actual]["actual"] += 1
		results[predicted]["predicted"] += 1
	for label in results:
		precision = 100*float(results[label]["hits"]) / results[label]["predicted"]
		recall = 100*float(results[label]["hits"]) / results[label]["actual"]
		print("{}: precision={:.2f}, recall={:.2f}".format(label, precision, recall))
	output = model.score(test_X, test_y)
	print("accuracy: {}".format(output))
	print("accuracy: {}".format(np.sum(test_pred==test_y)/len(test_pred)))
	np.save("predicted.txt", test_pred)
	np.save("actual.txt", test_y)

def run_baseline_arora_model(params):
	corpus = read_corpus(params.corpus)
	# get word vectors

if __name__ == '__main__':
	if params.features == "mostcommonclass":
		get_most_common_class_accuracies()
	elif params.features == "bow":
		run_baseline_BoW_model(params)
	elif params.features == "arora":
		run_baseline_arora_model(params)

