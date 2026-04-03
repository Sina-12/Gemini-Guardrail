import pandas as pd
from sklearn.model_selection import train_test_split

main = pd.read_csv('../data/full_annotations_with_source_text.csv', encoding='ISO-8859-1')

first_half = main[:260]
second_half = main[260:]



train1, test1 = train_test_split(first_half, random_state=123, train_size=0.9)
train2, test2 = train_test_split(second_half, random_state=123, train_size=0.9)

train1, dev1 = train_test_split(train1, random_state=123, train_size=(8/9))
train2, dev2 = train_test_split(train2, random_state=123, train_size=(8/9))




train = pd.concat([train1, train2], ignore_index=True)
dev = pd.concat([dev1, dev2], ignore_index=True)
test = pd.concat([test1, test2], ignore_index=True)


train.to_csv('train.csv', index=False)
dev.to_csv('dev.csv', index=False)
test.to_csv('test.csv', index=False)

