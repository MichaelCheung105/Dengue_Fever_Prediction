# -*- coding: utf-8 -*-
"""
Created on Tue Aug  7 09:55:28 2018

@author: CHEUNMI2
"""

# -*- coding: utf-8 -*-
"""
Created on Sat Jul 21 17:46:20 2018

@author: lupus
"""

# import necessary packages
import pandas as pd
import numpy as np
import os 
import re
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error as MAE
from catboost import CatBoostRegressor

# reading data
path = "C:\\Users\\lupus\\OneDrive\\GIT\\OwnProjects\\DengAI_Competition\\Data\\"
path = "D:\\%UserName%\\OneDrive - Orient Overseas Container Line Ltd\\Projects\\Playground\\Dengue_Fever_Prediction\\Data\\"
data = {}
for csv in os.listdir(path):
    data[re.sub(".csv", "", csv)] = pd.read_csv(path + csv)

training_X = data.pop("DengAI_Predicting_Disease_Spread_-_Training_Data_Features")
training_Y = data.pop("DengAI_Predicting_Disease_Spread_-_Training_Data_Labels")
submit_X = data.pop("DengAI_Predicting_Disease_Spread_-_Test_Data_Features")
submit_Y = data.pop("DengAI_Predicting_Disease_Spread_-_Submission_Format")

# joining data for train_test_split in the later stage
training = training_X.merge(training_Y, on=['city', 'year', 'weekofyear'], how='left')
submit = submit_X.merge(submit_Y, on=['city', 'year', 'weekofyear'], how='left')

# set datetime as index
training.index = pd.DatetimeIndex(training.week_start_date)
submit.index = pd.DatetimeIndex(submit.week_start_date)

# generate datetime features
training['week_start_date'] = pd.to_datetime(training['week_start_date'], format='%Y-%m-%d')
training['quarter'] = training.week_start_date.dt.quarter
training['month'] = training.week_start_date.dt.month
training['day'] = training.week_start_date.dt.day
training['month-day'] = training['month'].astype(str) + "-" + training['day'].astype(str)

submit['week_start_date'] = pd.to_datetime(submit['week_start_date'], format='%Y-%m-%d')
submit['quarter'] = submit.week_start_date.dt.quarter
submit['month'] = submit.week_start_date.dt.month
submit['day'] = submit.week_start_date.dt.day
submit['month-day'] = submit['month'].astype(str) + "-" + submit['day'].astype(str)

# Identify categorical features and numerical features
cat_features = ['city', 'month-day']
cat_index = [i for i,v in enumerate(training.columns) if v in cat_features]
num_index = [i for i,v in enumerate(training.columns) if v not in cat_features]

# Converstion of categorical variables
for feature in cat_features:
    training[feature] = training[feature].astype('category')
    submit[feature] = submit[feature].astype('category')

# Check if there is any NA
training.isnull().sum()
submit.isnull().sum()

# Explore correlation between variables
plt.figure(figsize=(20,20))
sns.heatmap(training.corr(), xticklabels=training.corr().columns, yticklabels=training.corr().columns, center=0, annot=True)
plt.savefig('heatmap_before_removal.jpg')

# Remove some highly correlated feature (absolute correlation > 0.9)
features_to_remove = ['quarter', 'month', 'reanalysis_sat_precip_amt_mm', 'reanalysis_specific_humidity_g_per_kg', 'reanalysis_avg_temp_k', 'reanalysis_tdtr_k']
features_to_remove_index = [i for i,v in enumerate(training.columns) if v in features_to_remove]
training.drop(training.columns[features_to_remove_index], axis=1, inplace=True)
submit.drop(submit.columns[features_to_remove_index], axis=1, inplace=True)

# Explore correlation between variables after removing highly correlated features
plt.figure(figsize=(20,20))
sns.heatmap(training.corr(), xticklabels=training.corr().columns, yticklabels=training.corr().columns, center=0, annot=True)
plt.savefig('heatmap_after_removal.jpg')

# Check if there is any NA
training.isnull().sum()
submit.isnull().sum()

# Fill NA of time related data using interpolate
training.iloc[:,num_index] = training.iloc[:,num_index].apply(lambda x: x.fillna(x.mean()))
submit.iloc[:,num_index] = submit.iloc[:,num_index].apply(lambda x: x.fillna(x.mean()))

# drop week_start_date before doing train_test_split
training.drop('week_start_date', axis=1, inplace=True)
submit.drop('week_start_date', axis=1, inplace=True)

"""Catboost model cv set"""
# train test split for train, test and cv
X_train, X_test, y_train, y_test = train_test_split(training.drop(['total_cases'], axis=1), training.total_cases, test_size=0.2, stratify=training.city, random_state=123)
X_train, X_cv, y_train, y_cv = train_test_split(X_train, y_train, test_size=0.25, stratify=X_train.city, random_state=123)

# build model
cat_index = [i for i,v in enumerate(X_train.columns) if v in cat_features]
model = CatBoostRegressor(iterations = 4000, learning_rate = 0.3, loss_function='MAE', eval_metric='MAE', use_best_model=True, random_seed=123)
model.fit(X_train, y_train, cat_features=cat_index, eval_set=(X_cv, y_cv))
y_pred = model.predict(X_test)
MAE(y_test, y_pred)
pd.DataFrame(data={'features':X_train.columns, 'importance':model.feature_importances_}).plot.bar(x='features', y='importance')

"""Catboost model submit set"""
# train test split for train, and cv
X_train, X_cv, y_train, y_cv = train_test_split(training.drop(['total_cases'], axis=1), training.total_cases, test_size=0.2, stratify=training.city, random_state=123)

# build model
cat_index = [i for i,v in enumerate(X_train.columns) if v in cat_features]
model = CatBoostRegressor(iterations = 4000, learning_rate = 0.3, loss_function='MAE', eval_metric='MAE', use_best_model=True, random_seed=123)
model.fit(X_train, y_train, cat_features=cat_index, eval_set=(X_cv, y_cv))
y_pred = model.predict(submit.drop(['total_cases'], axis=1))
submit_Y.total_cases = np.round(y_pred)
submit_Y.to_csv('prediction.csv', index=False)
