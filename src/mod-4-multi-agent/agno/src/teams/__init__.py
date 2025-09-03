"""
Agno Teams Implementation - Phase 1
Modern team architecture using Agno's native Team functionality
"""

from .agno_team_base import AgnoTeamBase
from .ubereats_eta_team import UberEatsETATeam

__all__ = [
    'AgnoTeamBase',
    'UberEatsETATeam'
]

# Version information
__version__ = "1.0.0"
__phase__ = "Phase 1 - Core Team Structure Migration"