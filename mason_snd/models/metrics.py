"""Metrics Models - Weighted scoring configuration.

Defines system-wide settings for weighted metrics calculation, balancing
effort scores (practice/preparation) and tournament performance (competition results).

Key Model:
    MetricsSettings: Global weights for effort vs. tournament points

Weighted Metrics System:
    - Combines effort_points (practice) and tournament_points (competition)
    - Configurable weights (default: 30% effort, 70% tournament)
    - Single settings record for entire system
    - Adjustable by admins via metrics settings page

Calculation:
    total_score = (effort_points * effort_weight) + (tournament_points * tournament_weight)
    
    Example (default weights):
        effort_points = 100 (from Effort_Score)
        tournament_points = 500 (from Tournament_Performance)
        total = (100 * 0.3) + (500 * 0.7) = 30 + 350 = 380

Purpose:
    - Reward both practice and competition
    - Adjust emphasis based on team philosophy
    - Enable fair comparison across members
    - Encourage consistent participation
"""

from ..extensions import db

class MetricsSettings(db.Model):
    """Global settings for weighted metrics calculation.
    
    Stores system-wide weight configuration for combining effort scores
    and tournament performance into unified metrics. Single record expected.
    
    Purpose:
        - Configure effort vs. tournament weight balance
        - Enable admin adjustment of scoring philosophy
        - Centralize metrics calculation parameters
        - Provide consistent scoring across all users
    
    Weight System:
        effort_weight:
            - Weight applied to effort_points (practice/preparation)
            - Default: 0.3 (30%)
            - Range: 0.0 - 1.0 (typically)
        
        tournament_weight:
            - Weight applied to tournament_points (competition results)
            - Default: 0.7 (70%)
            - Range: 0.0 - 1.0 (typically)
        
        Note:
            Weights don't need to sum to 1.0 (can emphasize one aspect more).
            Typical usage: sum to 1.0 for balanced 100% scoring.
    
    Metrics Calculation:
        Formula:
            total_score = (effort_points * effort_weight) + 
                         (tournament_points * tournament_weight)
        
        Where:
            effort_points = sum of all Effort_Score.score for user
            tournament_points = sum of all Tournament_Performance.points for user
        
        Used in:
            - User rankings (metrics dashboard)
            - Tier assignments (metrics tiers)
            - Performance analysis
            - Achievement tracking
    
    Columns:
        id: Primary key (single record expected)
        effort_weight: Weight for effort scores (Float, default 0.3)
        tournament_weight: Weight for tournament points (Float, default 0.7)
    
    Relationships:
        None (standalone settings table)
    
    Usage:
        Get settings:
            settings = MetricsSettings.query.first()
            if not settings:
                settings = MetricsSettings(
                    effort_weight=0.3,
                    tournament_weight=0.7
                )
                db.session.add(settings)
                db.session.commit()
        
        Update settings:
            settings = MetricsSettings.query.first()
            settings.effort_weight = 0.4
            settings.tournament_weight = 0.6
            db.session.commit()
        
        Calculate user score:
            settings = MetricsSettings.query.first()
            total = (user.effort_points * settings.effort_weight) + \
                   (user.tournament_points * settings.tournament_weight)
    
    Weight Adjustment Scenarios:
        Emphasize practice (40/60):
            - effort_weight = 0.4
            - tournament_weight = 0.6
            - Rewards consistent practice more
        
        Emphasize competition (20/80):
            - effort_weight = 0.2
            - tournament_weight = 0.8
            - Focuses on tournament results
        
        Equal weight (50/50):
            - effort_weight = 0.5
            - tournament_weight = 0.5
            - Balanced approach
    
    Admin Interface:
        - Accessible via metrics settings page (role >= 2)
        - Sliders or input fields for weight adjustment
        - Preview of impact on user rankings
        - Save updates to single MetricsSettings record
    
    Database Constraints:
        - Typically one record (id=1)
        - If multiple records, query .first() or .get(1)
        - Consider unique constraint or singleton pattern
    
    Note:
        Changing weights recalculates all user scores dynamically.
        No need to update existing score records (computed on the fly).
    """
    id = db.Column(db.Integer, primary_key=True)
    effort_weight = db.Column(db.Float, default=0.3)
    tournament_weight = db.Column(db.Float, default=0.7)
