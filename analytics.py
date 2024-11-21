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
        return "No Data", 0  # Indicate no data if insufficient points

    X = np.array([(d - dates[0]).days for d in dates]).reshape(-1, 1)
    y = np.array(scores)

    model = LinearRegression()
    model.fit(X, y)

    # Calculate percentage change if possible
    if scores[0] != 0:
        percentage_change = ((scores[-1] - scores[0]) / scores[0]) * 100
    else:
        percentage_change = float('inf')  # Handle division by zero

    # Enhanced trend logic using both slope and percentage change
    if model.coef_[0] > 0 and percentage_change > 10:  # Example threshold change
        trend = "Improving"
    elif model.coef_[0] < 0 and percentage_change < -10:  # Example threshold change
        trend = "Declining"
    else:
        trend = "Stable"

    next_prediction = model.predict([[X[-1][0] + 1]])[0]

    return trend, next_prediction

def projected_movements(participants, participant_predictions, weighted_scores):
    projected_changes = {}
    current_rankings = sorted(participants, key=lambda p: participant_predictions[p.id], reverse=True)
    projected_rankings = sorted(participants, key=lambda p: participant_predictions[p.id] + (participant_predictions[p.id] - weighted_scores[p.id]), reverse=True)

    for idx, participant in enumerate(current_rankings):
        projected_rank = projected_rankings.index(participant)
        if projected_rank < idx:
            projected_changes[participant.id] = 'up'
        elif projected_rank > idx:
            projected_changes[participant.id] = 'down'

    return projected_changes

def get_user_performance_slope(user_id):
    user_stats = Statistics.query.filter_by(user_id=user_id).order_by(Statistics.date).all()
    dates = [stat.date for stat in user_stats]
    scores = [stat.score for stat in user_stats]
    if len(dates) < 2:
        return 0  # Return a slope of 0 if not enough data
    X = np.array([(d - dates[0]).days for d in dates]).reshape(-1, 1)
    y = np.array(scores)
    model = LinearRegression()
    model.fit(X, y)
    return model.coef_[0]  # Return the slope

def calculate_weighted_score(points, user_id, max_trend_value=5):
    trend_slope = get_user_performance_slope(user_id)

    # Scale trend slope to a 1-100 range
    scaled_trend = (trend_slope / max_trend_value) * 100

    # Combine points and scaled trend
    weight_points = 0.7
    weight_trend = 0.3

    weighted_score = (weight_points * points) + (weight_trend * scaled_trend)
    return weighted_score





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
        return 0  # Similar to the trend, return 0 if not enough points to predict

    X = np.array([(d - dates[0]).days for d in dates]).reshape(-1, 1)
    y = np.array(scores)

    model = LinearRegression()
    model.fit(X, y)

    next_day_since_start = (dates[-1] - dates[0]).days + 1
    next_prediction = model.predict([[next_day_since_start]])[0]

    return next_prediction