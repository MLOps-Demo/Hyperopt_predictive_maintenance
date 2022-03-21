# -*- coding: utf-8 -*-
"""Predictive_maintenance_hyperopt.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Pp_Z4WyKOPTwrEbwUaeWPE1BdoaCiioY
"""

import numpy as np
import pandas as pd
#import warnings
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import plotly.express as px
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
#from pylab import rcParams
from imblearn.combine import SMOTETomek
from imblearn.under_sampling import NearMiss
import xgboost as xgb
from xgboost import XGBClassifier

from sklearn.metrics import classification_report, accuracy_score,confusion_matrix
from sklearn.metrics import precision_score, recall_score
from sklearn.metrics import plot_confusion_matrix
from sklearn.metrics import roc_curve, auc

#hyper opt implementation packages
from sklearn.ensemble import RandomForestClassifier 
from sklearn import metrics
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler 
from hyperopt import tpe, hp, fmin, STATUS_OK,Trials
from hyperopt.pyll.base import scope
import json

df=pd.read_csv('Data/predictive_maintenance.csv')

df['Target'].value_counts()

df.info()

le = LabelEncoder()
df['Type']         = le.fit_transform(df.loc[:,["Type"]].values)
df['Failure Type'] = le.fit_transform(df.loc[:,["Failure Type"]].values)

df = df.drop(["UDI","Product ID","Failure Type"],axis = 1)
df.head(5)

#divide numeric and categorical variable
df_numeric = df.loc[:,['Air temperature [K]','Process temperature [K]','Rotational speed [rpm]','Torque [Nm]','Tool wear [min]']]
df_cat    = df.loc[:,['Type']]

fig = plt.figure(figsize = (15,15))
ax  = fig.gca()
df_numeric.loc[:,['Air temperature [K]','Process temperature [K]','Rotational speed [rpm]','Torque [Nm]','Tool wear [min]']].hist(ax = ax)
plt.savefig('machine_histogram.png')

print(df_cat.value_counts())

# Observe distrubution of failures
df.groupby(['Type']).sum().plot(kind='pie', y='Target',autopct='%1.0f%%')
plt.savefig('Machine_type.png')

X  = df.iloc[:, :-1].values
y  = df.loc[:,['Target']].values

print(X.shape, y.shape)


#rcParams['figure.figsize'] = 14, 8
RANDOM_SEED = 42



# Implementing Oversampling for Handling Imbalanced 
smk = SMOTETomek(random_state=42)
X_res,y_res=smk.fit_resample(X,y)

print(X_res.shape,y_res.shape)

print(y.shape,y_res.shape)

X_train, X_test, y_train, y_test = train_test_split(X_res, y_res, test_size=0.2)

#parameter for optimization
space = {
    'max_depth' : hp.choice('max_depth', range(5, 30, 1)),
    'learning_rate' : hp.quniform('learning_rate', 0.01, 0.5, 0.01),
    'n_estimators' : hp.choice('n_estimators', range(20, 205, 5)),
    'gamma' : hp.quniform('gamma', 0, 0.50, 0.01),
    'min_child_weight' : hp.quniform('min_child_weight', 1, 10, 1),
    'subsample' : hp.quniform('subsample', 0.1, 1, 0.01),
    'colsample_bytree' : hp.quniform('colsample_bytree', 0.1, 1.0, 0.01)}

# method to apply hyperopt

def objective(space):

    #warnings.filterwarnings(action='ignore', category=DeprecationWarning)
    classifier = xgb.XGBClassifier(n_estimators = space['n_estimators'],
                            max_depth = int(space['max_depth']),
                            learning_rate = space['learning_rate'],
                            gamma = space['gamma'],
                            min_child_weight = space['min_child_weight'],
                            subsample = space['subsample'],
                            colsample_bytree = space['colsample_bytree']
                            )
    
    classifier.fit(X_train, y_train)

    # Applying k-Fold Cross Validation
    from sklearn.model_selection import cross_val_score
    accuracies = cross_val_score(estimator = classifier, X = X_train, y = y_train, cv = 10)
    CrossValMean = accuracies.mean()

    print("CrossValMean:", CrossValMean)

    return{'loss':1-CrossValMean, 'status': STATUS_OK }

#looking for best optimization parameters
trials = Trials()
best = fmin(fn=objective,
            space=space,
            algo=tpe.suggest,
            max_evals=40,
            trials=trials)

print("Best: ", best)

xgb_clf = XGBClassifier(n_estimators = best['n_estimators'],
                            max_depth = best['max_depth'],
                            learning_rate = best['learning_rate'],
                            gamma = best['gamma'],
                            min_child_weight = best['min_child_weight'],
                            subsample = best['subsample'],
                            colsample_bytree = best['colsample_bytree']
                        )
xgb_clf.fit(X_train, y_train)

y_pred_xgb   = xgb_clf.predict(X_test)

accuracy= accuracy_score(y_test, y_pred_xgb)*100
precision= precision_score(y_test, y_pred_xgb)*100
recall= recall_score(y_test, y_pred_xgb)*100

data= {'accuracy': accuracy,'precision':precision,'recall': recall }


with open('Output/accuracy.json', 'w') as f:
  json.dump(data,f,sort_keys=True,  indent=4, separators=(',', ': '))

# Performance Metrics
print("Test Accuracy (Target)       : ",accuracy_score(y_test, y_pred_xgb)*100,"%")
print("Test Precision (Target)      : ",precision_score(y_test, y_pred_xgb)*100,"%")
print("Test Recall (Target)         : ",recall_score(y_test, y_pred_xgb)*100,"%")

#plot cf matrix
cm = confusion_matrix(y_test, y_pred_xgb)
print(cm)

plot_confusion_matrix(xgb_clf, X_test, y_test)  
plt.savefig('Confusion_matrix.png')

test_fpr, test_tpr, te_thresholds = roc_curve(y_test, y_pred_xgb)
print(test_fpr)
print(test_tpr)

plt.subplots(1, figsize=(10,10))
plt.title('ROC  Characteristic')
a=plt.plot(test_fpr, test_tpr)
plt.plot([0, 1], ls="--")
plt.plot([0, 0], [1, 0] , c=".7"), plt.plot([1, 1] , c=".7")
plt.ylabel('True Positive Rate')
plt.xlabel('False Positive Rate')
#plt.show()
plt.savefig('auc.png')