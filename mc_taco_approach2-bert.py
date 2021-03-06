# -*- coding: utf-8 -*-
"""MC TACO - BERT.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/13_CLxt-Z9sqTwfLCq0aZsqNXLfaUbwrs
"""

!pip install bert-for-tf2
!pip install sentencepiece

# Commented out IPython magic to ensure Python compatibility.
try:
#     %tensorflow_version 2.x
except Exception:
    pass
import tensorflow as tf

import tensorflow_hub as hub

from tensorflow.keras import layers
import bert

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import math

df = pd.read_csv('/content/test_9442.tsv', delimiter='\t', header=None)

from google.colab import drive
drive.mount('/content/drive')

def data_preprocessing(df):
  df.columns=['Statement', 'Question', 'Answer', 'Label', 'Category']
  df.dropna(inplace=True)
  enc = LabelEncoder()
  df['Label'] = enc.fit_transform(df['Label'])
  enc2 = LabelEncoder()
  df['Category'] = enc2.fit_transform(df['Category'])
  return df

"""# New Section"""

df = data_preprocessing(df)

df.head()

df['Text'] = df['Statement']+df['Question']+df['Answer']

df = df.drop(['Statement','Question','Answer','Category'], axis=1)

df.head()

BertTokenizer = bert.bert_tokenization.FullTokenizer
bert_layer = hub.KerasLayer("https://tfhub.dev/tensorflow/bert_en_uncased_L-12_H-768_A-12/1",
                            trainable=False)
vocabulary_file = bert_layer.resolved_object.vocab_file.asset_path.numpy()
to_lower_case = bert_layer.resolved_object.do_lower_case.numpy()
tokenizer = BertTokenizer(vocabulary_file, to_lower_case)

def tokenize(text):
    return tokenizer.convert_tokens_to_ids(tokenizer.tokenize(text))

tokenize= [tokenize(text) for text in df['Text'] ]

len(tokenize)

y = df['Label'].values

tokenize = [(text, y[i]) for i, text in enumerate(tokenize)]

processed_dataset = tf.data.Dataset.from_generator(lambda: tokenize, output_types=(tf.int32, tf.int32))

processed_dataset

BATCH_SIZE = 32
batched_dataset = processed_dataset.padded_batch(BATCH_SIZE, padded_shapes=((None, ), ()))

next(iter(batched_dataset))

next(iter(batched_dataset))

TOTAL_BATCHES = math.ceil(len(tokenize) / BATCH_SIZE)
TEST_BATCHES = TOTAL_BATCHES // 10
batched_dataset.shuffle(TOTAL_BATCHES)
test_data = batched_dataset.take(TEST_BATCHES)
train_data = batched_dataset.skip(TEST_BATCHES)

class TEXT_MODEL(tf.keras.Model):
    
    def __init__(self,
                 vocabulary_size,
                 embedding_dimensions=128,
                 cnn_filters=50,
                 dnn_units=512,
                 model_output_classes=2,
                 dropout_rate=0.1,
                 training=False,
                 name="text_model"):
        super(TEXT_MODEL, self).__init__(name=name)
        
        self.embedding = layers.Embedding(vocabulary_size,
                                          embedding_dimensions)
        self.cnn_layer1 = layers.Conv1D(filters=cnn_filters,
                                        kernel_size=2,
                                        padding="valid",
                                        activation="relu")
        self.cnn_layer2 = layers.Conv1D(filters=cnn_filters,
                                        kernel_size=3,
                                        padding="valid",
                                        activation="relu")
        self.cnn_layer3 = layers.Conv1D(filters=cnn_filters,
                                        kernel_size=4,
                                        padding="valid",
                                        activation="relu")
        self.pool = layers.GlobalMaxPool1D()
        
        self.dense_1 = layers.Dense(units=dnn_units, activation="relu")
        self.dropout = layers.Dropout(rate=dropout_rate)
        if model_output_classes == 2:
            self.last_dense = layers.Dense(units=1,
                                           activation="sigmoid")
        else:
            self.last_dense = layers.Dense(units=model_output_classes,
                                           activation="softmax")
    
    def call(self, inputs, training):
        l = self.embedding(inputs)
        l_1 = self.cnn_layer1(l) 
        l_1 = self.pool(l_1) 
        l_2 = self.cnn_layer2(l) 
        l_2 = self.pool(l_2)
        l_3 = self.cnn_layer3(l)
        l_3 = self.pool(l_3) 
        
        concatenated = tf.concat([l_1, l_2, l_3], axis=-1) # (batch_size, 3 * cnn_filters)
        concatenated = self.dense_1(concatenated)
        concatenated = self.dropout(concatenated, training)
        model_output = self.last_dense(concatenated)
        
        return model_output

VOCAB_LENGTH = len(tokenizer.vocab)
EMB_DIM = 200
CNN_FILTERS = 100
DNN_UNITS = 256
OUTPUT_CLASSES = 2

DROPOUT_RATE = 0.2

NB_EPOCHS = 5

text_model = TEXT_MODEL ( vocabulary_size=VOCAB_LENGTH,
                        embedding_dimensions=EMB_DIM,
                        cnn_filters=CNN_FILTERS,
                        dnn_units=DNN_UNITS,
                        model_output_classes=OUTPUT_CLASSES,
                        dropout_rate=DROPOUT_RATE)



text_model.compile(loss="binary_crossentropy", optimizer="adam", metrics=['accuracy'])

text_model.fit(train_data, epochs=NB_EPOCHS)

results = text_model.evaluate(test_data)
print(results)

