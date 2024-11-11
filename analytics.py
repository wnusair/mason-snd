from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from models import User, Event, Tournament, Statistics
from sqlalchemy import func

def get_user_performance_trend(user_id):
    user_stats = Statistics.query.filter_by(user_id=user_id).order_by(Statistics.date).all()
    dates = [stat.date for stat in user_stats]
    scores = [stat.score for stat in user_stats]

    if len(dates) < 2:
        return None, None

    X = np.array([(d - dates[0]).days for d in dates]).reshape(-1, 1)
    y = np.array(scores)

    model = LinearRegression()
    model.fit(X, y)

    trend = "Improving" if model.coef_[0] > 0 else "Declining"
    next_prediction = model.predict([[X[-1][0] + 1]])[0]  # Predict next day's score

    return trend, next_prediction

def get_team_next_predicted_score():
    team_stats = Statistics.query.order_by(Statistics.date).all()
    if len(team_stats) < 2:
        return None  # Not enough data to predict

    # Aggregate scores weekly
    weekly_aggregates = {}
    for stat in team_stats:
        week_start = stat.date - timedelta(days=stat.date.weekday())  # Monday of the current week
        if week_start not in weekly_aggregates:
            weekly_aggregates[week_start] = 0
        weekly_aggregates[week_start] += stat.score

    dates = sorted(weekly_aggregates.keys())
    total_scores = [weekly_aggregates[date] for date in dates]

    if len(total_scores) < 2:
        return None  # Not enough data to predict

    X = np.array([(d - dates[0]).days // 7 for d in dates]).reshape(-1, 1)  # Change days to weeks
    y = np.array(total_scores)

    model = LinearRegression()
    model.fit(X, y)

    # Predict the next week's score
    next_week_since_start = X[-1][0] + 1
    next_prediction = model.predict([[next_week_since_start]])[0]

    return next_prediction

def get_team_improvement_rate():
    team_stats = Statistics.query.order_by(Statistics.date).all()
    if len(team_stats) < 2:
        return None
    
    first_date = team_stats[0].date
    X = np.array([(stat.date - first_date).days for stat in team_stats]).reshape(-1, 1)
    y = np.array([stat.score for stat in team_stats])
    
    model = LinearRegression()
    model.fit(X, y)
    
    return model.coef_[0] * 365  # Improvement rate per year

def get_user_next_predicted_score(user_id):
    user_stats = Statistics.query.filter_by(user_id=user_id).order_by(Statistics.date).all()
    dates = [stat.date for stat in user_stats]
    scores = [stat.score for stat in user_stats]

    if len(dates) < 2:
        return None  # Not enough data to predict

    X = np.array([(d - dates[0]).days for d in dates]).reshape(-1, 1)
    y = np.array(scores)

    model = LinearRegression()
    model.fit(X, y)

    # Predict the next score given the latest date
    next_day_since_start = (dates[-1] - dates[0]).days + 1
    next_prediction = model.predict([[next_day_since_start]])[0]

    return next_prediction