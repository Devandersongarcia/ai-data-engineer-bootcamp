"""
Data processing utilities for dashboard analytics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from geopy.distance import geodesic
import streamlit as st

class DataProcessor:
    """Process and analyze GPS and agent data for dashboard"""
    
    def __init__(self):
        # São Paulo zone boundaries (simplified)
        self.sao_paulo_zones = {
            'Vila_Madalena': {'lat': -23.5458, 'lon': -46.6919, 'radius_km': 2},
            'Itaim_Bibi': {'lat': -23.5756, 'lon': -46.6814, 'radius_km': 2},
            'Pinheiros': {'lat': -23.5631, 'lon': -46.7019, 'radius_km': 3},
            'Centro': {'lat': -23.5505, 'lon': -46.6333, 'radius_km': 4},
            'Brooklin': {'lat': -23.6136, 'lon': -46.6794, 'radius_km': 2}
        }
    
    def enrich_gps_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich GPS data with calculated metrics"""
        if df.empty:
            return df
        
        try:
            # Create a copy to avoid modifying original
            enriched_df = df.copy()
            
            # Calculate time-based features
            if '_timestamp' in enriched_df.columns:
                enriched_df['hour'] = pd.to_datetime(enriched_df['_timestamp']).dt.hour
                enriched_df['day_of_week'] = pd.to_datetime(enriched_df['_timestamp']).dt.dayofweek
                enriched_df['is_weekend'] = enriched_df['day_of_week'].isin([5, 6])
                
                # Peak hours (lunch: 11-14, dinner: 18-22)
                enriched_df['is_peak_hour'] = (
                    ((enriched_df['hour'] >= 11) & (enriched_df['hour'] <= 14)) |
                    ((enriched_df['hour'] >= 18) & (enriched_df['hour'] <= 22))
                )
            
            # Speed categories
            if 'speed_kph' in enriched_df.columns:
                enriched_df['speed_category'] = pd.cut(
                    enriched_df['speed_kph'],
                    bins=[-np.inf, 5, 25, 50, 80, np.inf],
                    labels=['Stopped', 'Slow', 'Normal', 'Fast', 'Excessive']
                )
            
            # Traffic severity scoring
            if 'traffic_density' in enriched_df.columns:
                traffic_scores = {
                    'light': 1, 'moderate': 2, 'heavy': 3, 'severe': 4
                }
                enriched_df['traffic_score'] = enriched_df['traffic_density'].map(traffic_scores).fillna(0)
            
            # Zone efficiency scoring
            enriched_df['zone_efficiency'] = self._calculate_zone_efficiency(enriched_df)
            
            # Distance calculations (if we have sequential data for same driver)
            enriched_df['distance_traveled'] = self._calculate_distances(enriched_df)
            
            # Anomaly severity
            if 'anomaly_flag' in enriched_df.columns:
                enriched_df['has_anomaly'] = enriched_df['anomaly_flag'].notna()
                enriched_df['anomaly_severity'] = self._categorize_anomalies(enriched_df)
            
            return enriched_df
            
        except Exception as e:
            st.error(f"Error enriching GPS data: {e}")
            return df
    
    def _calculate_zone_efficiency(self, df: pd.DataFrame) -> pd.Series:
        """Calculate efficiency score for each zone"""
        if 'zone_name' not in df.columns or 'speed_kph' not in df.columns:
            return pd.Series([0] * len(df))
        
        zone_efficiency = []
        
        for _, row in df.iterrows():
            zone = row.get('zone_name', 'Unknown')
            speed = row.get('speed_kph', 0)
            traffic = row.get('traffic_score', 2)  # Default moderate
            
            # Simple efficiency calculation
            # Higher speed, lower traffic = higher efficiency
            base_efficiency = min(speed / 30, 1.0)  # Normalize to max 30 km/h optimal
            traffic_penalty = (traffic - 1) * 0.2  # Reduce efficiency for heavy traffic
            
            efficiency = max(0, base_efficiency - traffic_penalty)
            zone_efficiency.append(efficiency * 100)  # Convert to percentage
        
        return pd.Series(zone_efficiency)
    
    def _calculate_distances(self, df: pd.DataFrame) -> pd.Series:
        """Calculate distance traveled between GPS points"""
        if len(df) < 2 or 'latitude' not in df.columns or 'longitude' not in df.columns:
            return pd.Series([0] * len(df))
        
        distances = [0]  # First point has no previous distance
        
        # Sort by driver and timestamp to ensure sequential calculation
        if 'driver_id' in df.columns and '_timestamp' in df.columns:
            df_sorted = df.sort_values(['driver_id', '_timestamp'])
            
            for i in range(1, len(df_sorted)):
                current_row = df_sorted.iloc[i]
                previous_row = df_sorted.iloc[i-1]
                
                # Only calculate distance if same driver
                if current_row['driver_id'] == previous_row['driver_id']:
                    try:
                        distance = geodesic(
                            (previous_row['latitude'], previous_row['longitude']),
                            (current_row['latitude'], current_row['longitude'])
                        ).kilometers
                        distances.append(distance)
                    except Exception:
                        distances.append(0)
                else:
                    distances.append(0)  # New driver, no previous distance
        else:
            distances.extend([0] * (len(df) - 1))
        
        return pd.Series(distances)
    
    def _categorize_anomalies(self, df: pd.DataFrame) -> pd.Series:
        """Categorize anomaly severity"""
        if 'anomaly_flag' not in df.columns:
            return pd.Series(['None'] * len(df))
        
        severity_mapping = {
            'speed_anomaly': 'Medium',
            'gps_spoofing': 'High',
            'teleportation': 'Critical',
            'route_deviation': 'Low',
            'time_anomaly': 'Medium'
        }
        
        return df['anomaly_flag'].map(severity_mapping).fillna('None')
    
    def calculate_zone_statistics(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Calculate comprehensive zone statistics"""
        if df.empty or 'zone_name' not in df.columns:
            return {}
        
        enriched_df = self.enrich_gps_data(df)
        zone_stats = {}
        
        for zone in enriched_df['zone_name'].unique():
            zone_data = enriched_df[enriched_df['zone_name'] == zone]
            
            zone_stats[zone] = {
                # Basic metrics
                'total_events': len(zone_data),
                'unique_drivers': zone_data['driver_id'].nunique() if 'driver_id' in zone_data else 0,
                'avg_speed': zone_data['speed_kph'].mean() if 'speed_kph' in zone_data else 0,
                'max_speed': zone_data['speed_kph'].max() if 'speed_kph' in zone_data else 0,
                
                # Advanced metrics
                'avg_efficiency': zone_data['zone_efficiency'].mean() if 'zone_efficiency' in zone_data else 0,
                'traffic_score': zone_data['traffic_score'].mean() if 'traffic_score' in zone_data else 0,
                'anomaly_count': zone_data['has_anomaly'].sum() if 'has_anomaly' in zone_data else 0,
                'anomaly_rate': (zone_data['has_anomaly'].sum() / len(zone_data) * 100) if len(zone_data) > 0 and 'has_anomaly' in zone_data else 0,
                
                # Time-based metrics
                'peak_hour_events': zone_data['is_peak_hour'].sum() if 'is_peak_hour' in zone_data else 0,
                'weekend_events': zone_data['is_weekend'].sum() if 'is_weekend' in zone_data else 0,
                
                # Trip stage distribution
                'trip_stages': zone_data['trip_stage'].value_counts().to_dict() if 'trip_stage' in zone_data else {},
                
                # Recent activity
                'last_activity': zone_data['_timestamp'].max() if '_timestamp' in zone_data else None,
                
                # Distance metrics
                'total_distance': zone_data['distance_traveled'].sum() if 'distance_traveled' in zone_data else 0
            }
        
        return zone_stats
    
    def calculate_driver_analytics(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Calculate comprehensive driver analytics"""
        if df.empty or 'driver_id' not in df.columns:
            return {}
        
        enriched_df = self.enrich_gps_data(df)
        driver_analytics = {}
        
        for driver_id in enriched_df['driver_id'].unique():
            driver_data = enriched_df[enriched_df['driver_id'] == driver_id]
            
            driver_analytics[driver_id] = {
                # Performance metrics
                'total_events': len(driver_data),
                'avg_speed': driver_data['speed_kph'].mean() if 'speed_kph' in driver_data else 0,
                'max_speed': driver_data['speed_kph'].max() if 'speed_kph' in driver_data else 0,
                'avg_efficiency': driver_data['zone_efficiency'].mean() if 'zone_efficiency' in driver_data else 0,
                
                # Coverage metrics
                'zones_visited': driver_data['zone_name'].nunique() if 'zone_name' in driver_data else 0,
                'favorite_zone': driver_data['zone_name'].mode().iloc[0] if 'zone_name' in driver_data and not driver_data['zone_name'].mode().empty else 'Unknown',
                'current_zone': driver_data.iloc[0]['zone_name'] if 'zone_name' in driver_data and len(driver_data) > 0 else 'Unknown',
                
                # Safety metrics
                'anomaly_count': driver_data['has_anomaly'].sum() if 'has_anomaly' in driver_data else 0,
                'high_speed_events': len(driver_data[driver_data['speed_kph'] > 60]) if 'speed_kph' in driver_data else 0,
                'safety_score': self._calculate_safety_score(driver_data),
                
                # Activity patterns
                'peak_hour_activity': (driver_data['is_peak_hour'].sum() / len(driver_data) * 100) if len(driver_data) > 0 and 'is_peak_hour' in driver_data else 0,
                'weekend_activity': (driver_data['is_weekend'].sum() / len(driver_data) * 100) if len(driver_data) > 0 and 'is_weekend' in driver_data else 0,
                
                # Trip analysis
                'trip_stages': driver_data['trip_stage'].value_counts().to_dict() if 'trip_stage' in driver_data else {},
                'current_stage': driver_data.iloc[0]['trip_stage'] if 'trip_stage' in driver_data and len(driver_data) > 0 else 'unknown',
                
                # Distance and time
                'total_distance': driver_data['distance_traveled'].sum() if 'distance_traveled' in driver_data else 0,
                'last_seen': driver_data['_timestamp'].max() if '_timestamp' in driver_data else None,
                'active_duration': self._calculate_active_duration(driver_data)
            }
        
        return driver_analytics
    
    def _calculate_safety_score(self, driver_data: pd.DataFrame) -> float:
        """Calculate safety score for a driver (0-100)"""
        if driver_data.empty:
            return 0.0
        
        base_score = 100.0
        
        # Deduct points for anomalies
        if 'has_anomaly' in driver_data.columns:
            anomaly_penalty = (driver_data['has_anomaly'].sum() / len(driver_data)) * 30
            base_score -= anomaly_penalty
        
        # Deduct points for excessive speed
        if 'speed_kph' in driver_data.columns:
            excessive_speed_events = len(driver_data[driver_data['speed_kph'] > 80])
            speed_penalty = (excessive_speed_events / len(driver_data)) * 25
            base_score -= speed_penalty
        
        # Consider traffic compliance
        if 'traffic_score' in driver_data.columns and 'speed_kph' in driver_data.columns:
            # Drivers who maintain reasonable speed in heavy traffic get bonus points
            heavy_traffic_data = driver_data[driver_data['traffic_score'] >= 3]
            if not heavy_traffic_data.empty:
                reasonable_speed_in_traffic = len(heavy_traffic_data[heavy_traffic_data['speed_kph'] <= 30])
                if len(heavy_traffic_data) > 0:
                    compliance_bonus = (reasonable_speed_in_traffic / len(heavy_traffic_data)) * 10
                    base_score += compliance_bonus
        
        return max(0.0, min(100.0, base_score))
    
    def _calculate_active_duration(self, driver_data: pd.DataFrame) -> float:
        """Calculate active duration in hours"""
        if driver_data.empty or '_timestamp' not in driver_data.columns:
            return 0.0
        
        if len(driver_data) < 2:
            return 0.0
        
        start_time = driver_data['_timestamp'].min()
        end_time = driver_data['_timestamp'].max()
        
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)
        if isinstance(end_time, str):
            end_time = pd.to_datetime(end_time)
        
        duration = (end_time - start_time).total_seconds() / 3600  # Convert to hours
        return max(0.0, duration)
    
    def calculate_system_health_metrics(self, gps_df: pd.DataFrame, agent_activities: List[Dict]) -> Dict[str, any]:
        """Calculate system health and performance metrics"""
        
        health_metrics = {
            'data_quality': self._assess_data_quality(gps_df),
            'agent_performance': self._assess_agent_performance(agent_activities),
            'system_efficiency': self._calculate_system_efficiency(gps_df),
            'anomaly_detection': self._assess_anomaly_detection(gps_df),
            'coverage_analysis': self._assess_zone_coverage(gps_df)
        }
        
        return health_metrics
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, any]:
        """Assess GPS data quality"""
        if df.empty:
            return {'score': 0, 'issues': ['No data available']}
        
        issues = []
        score = 100
        
        # Check for missing coordinates
        if 'latitude' in df.columns and 'longitude' in df.columns:
            invalid_coords = df[df['latitude'].isna() | df['longitude'].isna()]
            if not invalid_coords.empty:
                issues.append(f"{len(invalid_coords)} records with invalid coordinates")
                score -= 20
        
        # Check for unrealistic speeds
        if 'speed_kph' in df.columns:
            excessive_speeds = df[df['speed_kph'] > 150]  # Unrealistic for urban delivery
            if not excessive_speeds.empty:
                issues.append(f"{len(excessive_speeds)} records with unrealistic speeds")
                score -= 10
        
        # Check data freshness
        if '_timestamp' in df.columns:
            latest_data = df['_timestamp'].max()
            if isinstance(latest_data, str):
                latest_data = pd.to_datetime(latest_data)
            
            if latest_data and (datetime.now() - latest_data).total_seconds() > 300:  # 5 minutes
                issues.append("Data is not fresh (>5 minutes old)")
                score -= 15
        
        return {
            'score': max(0, score),
            'issues': issues if issues else ['No major issues detected'],
            'total_records': len(df)
        }
    
    def _assess_agent_performance(self, agent_activities: List[Dict]) -> Dict[str, any]:
        """Assess agent system performance"""
        if not agent_activities:
            return {'score': 0, 'active_agents': 0, 'issues': ['No agent activity detected']}
        
        recent_cutoff = datetime.now() - timedelta(minutes=10)
        recent_activities = [a for a in agent_activities if a.get('timestamp', datetime.min) >= recent_cutoff]
        
        agent_types = set(a.get('agent_type', 'Unknown') for a in recent_activities)
        
        score = len(agent_types) * 25  # 25 points per active agent type
        issues = []
        
        if len(agent_types) < 3:
            issues.append(f"Only {len(agent_types)} agent types active (expected 4+)")
        
        if len(recent_activities) < 5:
            issues.append("Low agent activity in last 10 minutes")
            score -= 20
        
        return {
            'score': min(100, score),
            'active_agents': len(agent_types),
            'recent_activities': len(recent_activities),
            'issues': issues if issues else ['Agent system performing well']
        }
    
    def _calculate_system_efficiency(self, df: pd.DataFrame) -> Dict[str, any]:
        """Calculate overall system efficiency"""
        if df.empty:
            return {'score': 0, 'metrics': {}}
        
        enriched_df = self.enrich_gps_data(df)
        
        if 'zone_efficiency' not in enriched_df.columns:
            return {'score': 50, 'metrics': {'error': 'Cannot calculate efficiency'}}
        
        avg_efficiency = enriched_df['zone_efficiency'].mean()
        
        # Calculate metrics
        metrics = {
            'avg_zone_efficiency': avg_efficiency,
            'high_efficiency_zones': len(enriched_df[enriched_df['zone_efficiency'] > 70]),
            'low_efficiency_zones': len(enriched_df[enriched_df['zone_efficiency'] < 30]),
            'peak_hour_efficiency': enriched_df[enriched_df['is_peak_hour']]['zone_efficiency'].mean() if 'is_peak_hour' in enriched_df else 0
        }
        
        return {
            'score': int(avg_efficiency),
            'metrics': metrics
        }
    
    def _assess_anomaly_detection(self, df: pd.DataFrame) -> Dict[str, any]:
        """Assess anomaly detection system"""
        if df.empty or 'anomaly_flag' not in df.columns:
            return {'score': 50, 'anomalies_detected': 0}
        
        total_anomalies = df['anomaly_flag'].notna().sum()
        anomaly_rate = (total_anomalies / len(df)) * 100
        
        # Ideal anomaly rate is 1-5% (too low = not detecting, too high = false positives)
        if 1 <= anomaly_rate <= 5:
            score = 100
        elif anomaly_rate < 1:
            score = 70  # Possibly missing anomalies
        elif anomaly_rate > 10:
            score = 40  # Too many false positives
        else:
            score = 80
        
        return {
            'score': score,
            'anomalies_detected': total_anomalies,
            'anomaly_rate': anomaly_rate
        }
    
    def _assess_zone_coverage(self, df: pd.DataFrame) -> Dict[str, any]:
        """Assess geographical coverage"""
        if df.empty or 'zone_name' not in df.columns:
            return {'score': 0, 'zones_covered': 0}
        
        zones_covered = df['zone_name'].nunique()
        total_expected_zones = len(self.sao_paulo_zones)
        
        coverage_percentage = (zones_covered / total_expected_zones) * 100
        
        return {
            'score': min(100, coverage_percentage),
            'zones_covered': zones_covered,
            'total_zones': total_expected_zones,
            'coverage_percentage': coverage_percentage
        }