"""Train a sequence to sequence model.

This script is sourced from Siraj Rival
https://github.com/llSourcell/How_to_make_a_text_summarizer/blob/master/train.ipynb
"""
import os
import time
import _pickle as pickle
import random
import argparse

import numpy as np
from keras.preprocessing import sequence

from keras.callbacks import TensorBoard

import config
from sample_gen import gensamples
from utils import prt, load_embedding, process_vocab, load_split_data
from model import create_model, inspect_model
from generate import gen
from constants import FN1, seed, nb_unknown_words


# you should use GPU...
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
# ...but if it is busy then you always can fall back to your CPU with
# os.environ['THEANO_FLAGS'] = 'device=cpu,floatX=float32'

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--batch-size', type=int, default=32, help='input batch size')
parser.add_argument('--epochs', type=int, default=10, help='number of epochs')
parser.add_argument('--rnn-size', type=int, default=512, help='size of RNN layers')
parser.add_argument('--rnn-layers', type=int, default=3, help='number of RNN layers')
parser.add_argument('--nsamples', type=int, default=640, help='number of samples per epoch')
parser.add_argument('--nflips', type=int, default=0, help='number of flips')
parser.add_argument('--temperature', type=float, default=.8, help='RNN temperature')
parser.add_argument('--lr', type=float, default=0.0001, help='learning rate, default=0.0001')
args = parser.parse_args()
batch_size = args.batch_size

# set sample sizes
nb_train_samples = np.int(np.floor(args.nsamples / batch_size)) * batch_size  # num training samples
nb_val_samples = nb_train_samples  # num validation samples

# seed weight initialization
random.seed(seed)
np.random.seed(seed)

embedding, idx2word, word2idx, glove_idx2idx = load_embedding(nb_unknown_words)
vocab_size, embedding_size = embedding.shape
oov0 = vocab_size - nb_unknown_words
idx2word = process_vocab(idx2word, vocab_size, oov0, nb_unknown_words)
X_train, X_test, Y_train, Y_test = load_split_data(nb_val_samples, seed)

# print a sample recipe to make sure everything looks right
print('Random head, description:')
i = 811
prt('H', Y_train[i], idx2word)
prt('D', X_train[i], idx2word)

model = create_model(
    vocab_size=vocab_size,
    embedding_size=embedding_size,
    LR=args.lr,
    embedding=embedding,
    rnn_layers=args.rnn_layers,
    rnn_size=args.rnn_size,
)
inspect_model(model)

# load pre-trained model weights
FN1_filename = os.path.join(config.path_models, '{}.hdf5'.format(FN1))
if FN1 and os.path.exists(FN1_filename):
    model.load_weights(FN1_filename)
    print('Model weights loaded from {}'.format(FN1_filename))

# print samples before training
gensamples(
    skips=2,
    k=10,
    batch_size=batch_size,
    short=False,
    temperature=args.temperature,
    use_unk=True,
    model=model,
    sequence=sequence,
    data=(X_test, Y_test),
    idx2word=idx2word,
    oov0=oov0,
    glove_idx2idx=glove_idx2idx,
    vocab_size=vocab_size,
    nb_unknown_words=nb_unknown_words,
)

r = next(gen(X_train, Y_train, batch_size=batch_size, nb_batches=None, nflips=None, model=None, debug=False, oov0=oov0, glove_idx2idx=glove_idx2idx, vocab_size=vocab_size, nb_unknown_words=nb_unknown_words, idx2word=idx2word))
valgen = gen(X_test, Y_test, batch_size=batch_size, nb_batches=3, nflips=None, model=None, debug=False, oov0=oov0, glove_idx2idx=glove_idx2idx, vocab_size=vocab_size, nb_unknown_words=nb_unknown_words, idx2word=idx2word)

# Train
history = {}
traingen = gen(X_train, Y_train, batch_size=batch_size, nb_batches=None, nflips=args.nflips, model=model, debug=False, oov0=oov0, glove_idx2idx=glove_idx2idx, vocab_size=vocab_size, nb_unknown_words=nb_unknown_words, idx2word=idx2word)
valgen = gen(X_test, Y_test, batch_size=batch_size, nb_batches=nb_val_samples // batch_size, nflips=None, model=None, debug=False, oov0=oov0, glove_idx2idx=glove_idx2idx, vocab_size=vocab_size, nb_unknown_words=nb_unknown_words, idx2word=idx2word)

callbacks = [TensorBoard(
    log_dir=os.path.join(config.path_logs, str(time.time())),
    histogram_freq=2, write_graph=False, write_images=False)]

h = model.fit_generator(
    traingen, samples_per_epoch=nb_train_samples,
    nb_epoch=args.epochs, validation_data=valgen, nb_val_samples=nb_val_samples,
    callbacks=callbacks,
)
for k, v in h.history.items():
    history[k] = history.get(k, []) + v
with open(os.path.join(config.path_models, 'history.pkl'), 'wb') as fp:
    pickle.dump(history, fp, -1)
model.save_weights(FN1_filename, overwrite=True)

# print samples after training
gensamples(
    skips=2,
    k=10,
    batch_size=batch_size,
    short=False,
    temperature=args.temperature,
    use_unk=True,
    model=model,
    sequence=sequence,
    data=(X_test, Y_test),
    idx2word=idx2word,
    oov0=oov0,
    glove_idx2idx=glove_idx2idx,
    vocab_size=vocab_size,
    nb_unknown_words=nb_unknown_words,
)
