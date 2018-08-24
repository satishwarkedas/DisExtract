"""
Generate visualization for the model
methods accept data passed in from outside
"""
import numpy as np
import itertools
import torch
from scipy.special import expit as sigmoid
from data import get_batch
from torch.autograd import Variable


def collect_type_errors(dis_net, data, word_vec, target_marker_id, batch_size=512):
    """
    :param dis_net: Model
    :param data: Either valid or test or combined, should be a dictionary
    :param word_vec: obtained after executing `build_vocab()` method
    :return: (type1_list, type2_list)
    """
    dis_net.eval()

    # it will only be "valid" during retraining (fine-tuning)
    s1 = data['s1']
    s2 = data['s2']  # if eval_type == 'valid' else test['s2']
    target = data['label']

    # valid_preds, valid_labels = [], []
    correct_list, type_one_list, type_two_list = [], [], []
    num_pred_made = 0.
    num_target_marker = 0.

    for i in range(0, len(s1), batch_size):
        # prepare batch
        s1_batch, s1_len = get_batch(s1[i:i + batch_size], word_vec)
        s2_batch, s2_len = get_batch(s2[i:i + batch_size], word_vec)
        s1_batch, s2_batch = Variable(s1_batch.cuda()), Variable(s2_batch.cuda())
        tgt_batch = Variable(torch.LongTensor(target[i:i + batch_size])).cuda()

        # model forward
        output = dis_net((s1_batch, s1_len), (s2_batch, s2_len))

        pred = output.data.max(1)[1]
        # correct += pred.long().eq(tgt_batch.data.long()).cpu().sum()

        # we collect samples
        labels = target[i:i + batch_size]
        preds = pred.cpu().numpy()

        # analyze and collect Type I and Type II
        counter = 0
        for p, l in itertools.izip(preds.tolist(), labels.tolist()):
            # false positive, Type I error
            if p == target_marker_id and l != target_marker_id:
                type_one_list.append([s1[i + counter], s2[i + counter], p, l])
            elif p != target_marker_id and l == target_marker_id:
                type_two_list.append([s1[i + counter], s2[i + counter], p, l])
            elif p == l:
                correct_list.append([s1[i + counter], s2[i + counter], p, l])
            counter += 1

            if p == target_marker_id:
                num_pred_made += 1
            if l == target_marker_id:
                num_target_marker += 1

        if i % 100 == 0:
            print("processed {}".format(i))

    return correct_list, type_one_list, type_two_list, num_pred_made, num_target_marker


# propagate a three-part
def propagate_three(a, b, c, activation):
    a_contrib = 0.5 * (activation(a + c) - activation(c) + activation(a + b + c) - activation(b + c))
    b_contrib = 0.5 * (activation(b + c) - activation(c) + activation(a + b + c) - activation(a + c))
    return a_contrib, b_contrib, activation(c)


# propagate tanh nonlinearity
def propagate_tanh_two(a, b):
    return 0.5 * (np.tanh(a) + (np.tanh(a + b) - np.tanh(b))), 0.5 * (np.tanh(b) + (np.tanh(a + b) - np.tanh(a)))


def tiles_to_cd(texts):
    starts, stops = [], []
    tiles = texts
    L = tiles.shape[0]
    for c in range(tiles.shape[1]):
        text = tiles[:, c]
        start = 0
        stop = L - 1
        while text[start] == 0:
            start += 1
        while text[stop] == 0:
            stop -= 1
        starts.append(start)
        stops.append(stop)
    return starts, stops

# pytorch needs to return each input as a column
# return batch_size x L tensor
def gen_tiles(text, fill=0,
              method='cd', prev_text=None, sweep_dim=1):
    L = text.shape[0]
    texts = np.zeros((L - sweep_dim + 1, L), dtype=np.int)
    for start in range(L - sweep_dim + 1):
        end = start + sweep_dim
        if method == 'occlusion':
            text_new = np.copy(text).flatten()
            text_new[start:end] = fill
        elif method == 'build_up' or method == 'cd':
            text_new = np.zeros(L)
            text_new[start:end] = text[start:end]
        texts[start] = np.copy(text_new)
    return texts

# adapted from github acd
class CDLSTM(object):
    def __init__(self, model, glove_path):
        self.model = model
        weights = model.encoder.enc_lstm.state_dict()

        self.hidden_dim = model.encoder.enc_lstm_dim

        self.W_ii, self.W_if, self.W_ig, self.W_io = np.split(weights['weight_ih_l0'], 4, 0)
        self.W_hi, self.W_hf, self.W_hg, self.W_ho = np.split(weights['weight_hh_l0'], 4, 0)
        self.b_i, self.b_f, self.b_g, self.b_o = np.split(weights['bias_ih_l0'].numpy() + weights['bias_hh_l0'].numpy(),
                                                          4)

        self.word_emb_dim = 300
        self.glove_path = glove_path

        self.classifiers = []
        for c in self.model.classifier:
            self.classifiers.append((c.weight.data.numpy(), c.bias.data.numpy()))

    def classify(self, u, v):
        # note that u, v could be positional!! don't mix the two
        final_res = np.concatenate([u, v, u - v, u * v, (u + v) / 2.])
        for c in self.classifiers:
            w, b = c
            final_res = np.dot(final_res, w) + b
        return final_res

    def get_word_dict(self, sentences, tokenize=True, already_split=False):
        # create vocab of words
        word_dict = {}
        if tokenize:
            from nltk.tokenize import word_tokenize
        if not already_split:
            sentences = [s.split() if not tokenize else word_tokenize(s)
                         for s in sentences]
        for sent in sentences:
            for word in sent:
                if word not in word_dict:
                    word_dict[word] = ''
        word_dict['<s>'] = ''
        word_dict['</s>'] = ''
        return word_dict

    def get_glove(self, word_dict):
        assert hasattr(self, 'glove_path'), \
            'warning : you need to set_glove_path(glove_path)'
        # create word_vec with glove vectors
        word_vec = {}
        with open(self.glove_path) as f:
            for line in f:
                word, vec = line.split(' ', 1)
                if word in word_dict:
                    word_vec[word] = np.fromstring(vec, sep=' ')
        print('Found {0}(/{1}) words with glove vectors'.format(
            len(word_vec), len(word_dict)))
        return word_vec

    def build_vocab(self, sentences, tokenize=True, already_split=False):
        assert hasattr(self, 'glove_path'), 'warning : you need \
                                             to set_glove_path(glove_path)'
        word_dict = self.get_word_dict(sentences, tokenize, already_split)
        self.word_vec = self.get_glove(word_dict)
        print('Vocab size : {0}'.format(len(self.word_vec)))

    def prepare_samples(self, sentences, tokenize, verbose, no_sort=False, already_split=False):
        if tokenize:
            from nltk.tokenize import word_tokenize
        if not already_split:
            sentences = [['<s>'] + s.split() + ['</s>'] if not tokenize else
                         ['<s>'] + word_tokenize(s) + ['</s>'] for s in sentences]
        n_w = np.sum([len(x) for x in sentences])

        # filters words without glove vectors
        for i in range(len(sentences)):
            s_f = [word for word in sentences[i] if word in self.word_vec]
            if not s_f:
                import warnings
                warnings.warn('No words in "{0}" (idx={1}) have glove vectors. \
                               Replacing by "</s>"..'.format(sentences[i], i))
                s_f = ['</s>']
            sentences[i] = s_f

        lengths = np.array([len(s) for s in sentences])
        n_wk = np.sum(lengths)
        if verbose:
            print('Nb words kept : {0}/{1} ({2} %)'.format(
                n_wk, n_w, round((100.0 * n_wk) / n_w, 2)))

        if no_sort:
            # technically "forward" method is already sorting
            return sentences, lengths

        # sort by decreasing length
        lengths, idx_sort = np.sort(lengths)[::-1], np.argsort(-lengths)
        sentences = np.array(sentences)[idx_sort]

        return sentences, lengths, idx_sort

    def get_batch(self, batch):
        # sent in batch in decreasing order of lengths
        # batch: (bsize, max_len, word_dim)
        embed = np.zeros((len(batch[0]), len(batch), self.word_emb_dim))

        for i in range(len(batch)):
            for j in range(len(batch[i])):
                embed[j, i, :] = self.word_vec[batch[i][j]]

        # (T, bsize, word_dim)
        return embed

    def get_word_level_scores(self, sentA, sentB):
        """
        :param sentence: ['a', 'b', 'c', ...]
        :return:
        """
        # texts = gen_tiles(text_orig, method='cd', sweep_dim=1).transpose()
        # starts, stops = tiles_to_cd(texts)
        # [0, 1, 2,...], [0, 1, 2,...]

        sent_A, _, _ = self.prepare_samples([sentA], tokenize=False, verbose=True, already_split=True)
        sent_B, _, _ = self.prepare_samples([sentB], tokenize=False, verbose=True, already_split=True)

        h_A = np.sum(self.cd_text(sent_A, start=0, stop=len(sentA)))
        h_B = np.sum(self.cd_text(sent_B, start=0, stop=len(sentB)))

        # compute A, treat B as fixed
        starts, stops = range(len(sentA)), range(len(sentA))
        scores_A = np.array([self.classify(self.cd_text(sent_A, start=starts[i], stop=stops[i])[0], h_B)
                           for i in range(len(starts))])

        # compute B, treat A as fixed
        starts, stops = range(len(sentB)), range(len(sentB))
        scores_B = np.array([self.classify(h_A, self.cd_text(sent_B, start=starts[i], stop=stops[i])[0])
                             for i in range(len(starts))])

        # (sent_len, num_label)
        return scores_A, scores_B

    def cd_text(self, sentences, start, stop):

        # word_vecs = self.model.embed(batch.text)[:, 0].data
        word_vecs = self.get_batch(sentences).squeeze()

        T = word_vecs.size
        relevant = np.zeros((T, self.hidden_dim))
        irrelevant = np.zeros((T, self.hidden_dim))
        relevant_h = np.zeros((T, self.hidden_dim))
        irrelevant_h = np.zeros((T, self.hidden_dim))
        for i in range(T):
            if i > 0:
                prev_rel_h = relevant_h[i - 1]
                prev_irrel_h = irrelevant_h[i - 1]
            else:
                prev_rel_h = np.zeros(self.hidden_dim)
                prev_irrel_h = np.zeros(self.hidden_dim)

            rel_i = np.dot(self.W_hi, prev_rel_h)
            rel_g = np.dot(self.W_hg, prev_rel_h)
            rel_f = np.dot(self.W_hf, prev_rel_h)
            rel_o = np.dot(self.W_ho, prev_rel_h)
            irrel_i = np.dot(self.W_hi, prev_irrel_h)
            irrel_g = np.dot(self.W_hg, prev_irrel_h)
            irrel_f = np.dot(self.W_hf, prev_irrel_h)
            irrel_o = np.dot(self.W_ho, prev_irrel_h)

            if i >= start and i <= stop:
                rel_i = rel_i + np.dot(self.W_ii, word_vecs[i])
                rel_g = rel_g + np.dot(self.W_ig, word_vecs[i])
                rel_f = rel_f + np.dot(self.W_if, word_vecs[i])
                rel_o = rel_o + np.dot(self.W_io, word_vecs[i])
            else:
                irrel_i = irrel_i + np.dot(self.W_ii, word_vecs[i])
                irrel_g = irrel_g + np.dot(self.W_ig, word_vecs[i])
                irrel_f = irrel_f + np.dot(self.W_if, word_vecs[i])
                irrel_o = irrel_o + np.dot(self.W_io, word_vecs[i])

            rel_contrib_i, irrel_contrib_i, bias_contrib_i = propagate_three(rel_i, irrel_i, self.b_i, sigmoid)
            rel_contrib_g, irrel_contrib_g, bias_contrib_g = propagate_three(rel_g, irrel_g, self.b_g, np.tanh)

            relevant[i] = rel_contrib_i * (rel_contrib_g + bias_contrib_g) + bias_contrib_i * rel_contrib_g
            irrelevant[i] = irrel_contrib_i * (rel_contrib_g + irrel_contrib_g + bias_contrib_g) + (
                                                                                                   rel_contrib_i + bias_contrib_i) * irrel_contrib_g

            if i >= start and i < stop:
                relevant[i] += bias_contrib_i * bias_contrib_g
            else:
                irrelevant[i] += bias_contrib_i * bias_contrib_g

            if i > 0:
                rel_contrib_f, irrel_contrib_f, bias_contrib_f = propagate_three(rel_f, irrel_f, self.b_f, sigmoid)
                relevant[i] += (rel_contrib_f + bias_contrib_f) * relevant[i - 1]
                irrelevant[i] += (rel_contrib_f + irrel_contrib_f + bias_contrib_f) * irrelevant[
                    i - 1] + irrel_contrib_f * \
                             relevant[i - 1]

            o = sigmoid(np.dot(self.W_io, word_vecs[i]) + np.dot(self.W_ho, prev_rel_h + prev_irrel_h) + self.b_o)
            rel_contrib_o, irrel_contrib_o, bias_contrib_o = propagate_three(rel_o, irrel_o, self.b_o, sigmoid)
            new_rel_h, new_irrel_h = propagate_tanh_two(relevant[i], irrelevant[i])
            # relevant_h[i] = new_rel_h * (rel_contrib_o + bias_contrib_o)
            # irrelevant_h[i] = new_rel_h * (irrel_contrib_o) + new_irrel_h * (rel_contrib_o + irrel_contrib_o + bias_contrib_o)
            relevant_h[i] = o * new_rel_h
            irrelevant_h[i] = o * new_irrel_h

        return relevant_h[T - 1], irrelevant_h[T - 1]

        # Sanity check: scores + irrel_scores should equal the LSTM's output minus model.hidden_to_label.bias
        # we actually apply to all the linear layers to get the final influence

        # scores = np.dot(self.W_out, relevant_h[T - 1])
        # irrel_scores = np.dot(self.W_out, irrelevant_h[T - 1])

        # scores = self.classify(relevant_h[T - 1])
        # irrel_scores = self.classify(irrelevant_h[T - 1])

        # (num_classes)
        # return scores
