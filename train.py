import torch
import torch.nn as nn
from torch.autograd import Variable

import sys
import json
import pdb
import time
import numpy as np
import argparse
from data_loader import get_loader
from masked_cel import compute_loss

from model import Embedding, UtteranceEncoder, ContextEncoder, HREDDecoder, HRED, LatentVariableEncoder
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


def main(config):
    dictionary = json.load(open('./dictionary.json'))
    vocab_size = len(dictionary)
    word_embedding_dim = 300
    print("Vocabulary size:", len(dictionary))

    print("Loading word vecotrs.")
    word2vec_file = open('./word2vec.vector')
    word_vectors = np.random.uniform(low=-0.25, high=0.25, size=(vocab_size, word_embedding_dim))
    next(word2vec_file)
    for line in word2vec_file:
        word, vec = line.split(' ', 1)
        if word in dictionary:
            word_vectors[dictionary[word]] = np.fromstring(vec, dtype=np.float32, sep=' ')

    train_loader = get_loader('./data/train.src', './data/train.tgt', dictionary, 64)
    dev_loader = get_loader('./data/valid.src', './data/valid.tgt', dictionary, 200)

    hidden_size = 512
    cenc_input_size = hidden_size * 2

    if not config.use_saved:
        hred = HRED(dictionary, vocab_size, word_embedding_dim, word_vectors, hidden_size)
    else:
        hred = torch.load('hred.pt')
        hred.flatten_parameters()
    params = hred.parameters()
    optimizer = torch.optim.SGD(params, lr=0.25, momentum=0.99)
    #optimizer = torch.optim.Adam(params, lr=30)

    for it in range(10):
        # eval on dev
        dev_loss = 0
        count = 0
        for i, (src_seqs, src_lengths, indices, trg_seqs, trg_lengths, ctc_lengths) in enumerate(dev_loader):
            dev_loss += hred.loss(src_seqs, src_lengths, indices, trg_seqs, trg_lengths, ctc_lengths).data[0]
            count += 1
        print('dev loss: {}'.format(dev_loss / count))

        ave_loss = 0
        last_time = time.time()
        for _, (src_seqs, src_lengths, indices, trg_seqs, trg_lengths, ctc_lengths) in enumerate(train_loader):
            if _ % config.print_every_n_batches == 1:
                print(ave_loss / min(_, config.print_every_n_batches), time.time() - last_time)
                torch.save(hred, 'hred.pt')
                ave_loss = 0
            loss = hred.loss(src_seqs, src_lengths, indices, trg_seqs, trg_lengths, ctc_lengths)
            ave_loss += loss.data[0]
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm(params, 0.1)
            optimizer.step()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vhred', type=bool, default=False)
    parser.add_argument('--use_saved', type=bool, default=False)
    parser.add_argument('--print_every_n_batches', type=int, default=1000)
    config = parser.parse_args()
    main(config)
