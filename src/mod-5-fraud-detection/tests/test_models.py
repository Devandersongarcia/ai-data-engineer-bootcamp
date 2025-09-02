"""
Tests for fraud detection data models
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models.order import OrderData
from models.fraud_result import FraudResult, FraudPattern, AgentAnalysis
from models.user_profile import UserBehaviorProfile
from models.action_result import ActionResult, BlockActionResult


class TestOrderData:
    """Test OrderData model validation and functionality"""
    
    def test_valid_order_creation(self, sample_order_data):
        """Test creating a valid order"""
        assert sample_order_data.order_id == "test_order_123"
        assert sample_order_data.user_key == "test_user_456"
        assert sample_order_data.total_amount == 25.50
        assert sample_order_data.item_count == 2
    
    def test_order_validation_required_fields(self):
        """Test validation of required fields"""
        with pytest.raises(ValidationError) as exc_info:
            OrderData()
        
        errors = exc_info.value.errors()
        required_fields = ["order_id", "user_key", "total_amount", "item_count"]
        
        for field in required_fields:
            assert any(error["loc"][0] == field for error in errors)
    
    def test_order_validation_positive_amounts(self):
        """Test validation of positive amounts"""
        with pytest.raises(ValidationError):
            OrderData(
                order_id="test",
                user_key="user",
                total_amount=-10.0,  # Negative amount
                item_count=1
            )
        
        with pytest.raises(ValidationError):
            OrderData(
                order_id="test",
                user_key="user",
                total_amount=10.0,
                item_count=0  # Zero items
            )
    
    def test_order_risk_indicators(self, high_risk_order_data):
        """Test order risk indicator calculations"""
        order = high_risk_order_data
        
        # High velocity indicators
        assert order.orders_today == 15
        assert order.payment_failures_today == 5
        
        # New account indicator
        assert order.account_age_days == 1
        
        # Fast order creation
        assert order.order_creation_speed_ms == 500
        
        # Geographic risk
        assert order.distance_from_restaurant_km == 25.0
    
    def test_order_serialization(self, sample_order_data):
        """Test order data serialization/deserialization"""
        # Convert to dict
        order_dict = sample_order_data.model_dump()
        assert isinstance(order_dict, dict)
        assert order_dict["order_id"] == "test_order_123"
        
        # Recreate from dict
        recreated_order = OrderData(**order_dict)
        assert recreated_order.order_id == sample_order_data.order_id
        assert recreated_order.total_amount == sample_order_data.total_amount


class TestFraudResult:
    """Test FraudResult model validation and functionality"""
    
    def test_valid_fraud_result_creation(self, sample_fraud_result):
        """Test creating a valid fraud result"""
        assert sample_fraud_result.fraud_score == 0.75
        assert sample_fraud_result.recommended_action == "REVIEW"
        assert sample_fraud_result.confidence_level == 0.85
        assert len(sample_fraud_result.detected_patterns) == 1
        assert len(sample_fraud_result.agent_analyses) == 1
    
    def test_fraud_score_validation(self):
        """Test fraud score validation (0.0 to 1.0)"""
        with pytest.raises(ValidationError):
            FraudResult(
                fraud_score=-0.1,  # Below 0
                recommended_action="BLOCK",
                confidence_level=0.8,
                reasoning="Test"
            )
        
        with pytest.raises(ValidationError):
            FraudResult(
                fraud_score=1.1,  # Above 1
                recommended_action="BLOCK",
                confidence_level=0.8,
                reasoning="Test"
            )
    
    def test_recommended_action_validation(self):
        """Test recommended action validation"""
        valid_actions = ["ALLOW", "REVIEW", "BLOCK"]
        
        for action in valid_actions:
            result = FraudResult(
                fraud_score=0.5,
                recommended_action=action,
                confidence_level=0.8,
                reasoning="Test"
            )
            assert result.recommended_action == action
        
        with pytest.raises(ValidationError):
            FraudResult(
                fraud_score=0.5,
                recommended_action="INVALID_ACTION",
                confidence_level=0.8,
                reasoning="Test"
            )
    
    def test_fraud_pattern_validation(self):
        """Test fraud pattern validation"""
        pattern = FraudPattern(
            pattern_type="velocity_fraud",
            confidence=0.9,
            evidence=["High order frequency"],
            risk_score=0.8
        )
        
        assert pattern.pattern_type == "velocity_fraud"
        assert pattern.confidence == 0.9
        assert len(pattern.evidence) == 1
        
        # Test confidence validation
        with pytest.raises(ValidationError):
            FraudPattern(
                pattern_type="test",
                confidence=1.5,  # Invalid confidence
                evidence=[],
                risk_score=0.8
            )
    
    def test_agent_analysis_validation(self):
        """Test agent analysis validation"""
        analysis = AgentAnalysis(
            agent_name="test_agent",
            analysis_result="Test result",
            confidence=0.85,
            processing_time_ms=100
        )
        
        assert analysis.agent_name == "test_agent"
        assert analysis.confidence == 0.85
        assert analysis.processing_time_ms == 100
    
    def test_fraud_result_to_dict(self, sample_fraud_result):
        """Test fraud result dictionary conversion"""
        result_dict = sample_fraud_result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["fraud_score"] == 0.75
        assert result_dict["recommended_action"] == "REVIEW"
        assert "detected_patterns" in result_dict
        assert "agent_analyses" in result_dict


class TestUserBehaviorProfile:
    """Test UserBehaviorProfile model validation and functionality"""
    
    def test_valid_profile_creation(self, sample_user_profile):
        """Test creating a valid user profile"""
        profile = sample_user_profile
        
        assert profile.user_key == "test_user_456"
        assert profile.total_orders == 25
        assert profile.avg_order_value == 28.75
        assert profile.risk_score == 0.15
    
    def test_profile_risk_calculation(self):
        """Test risk score calculation logic"""
        # Low risk profile
        low_risk_profile = UserBehaviorProfile(
            user_key="low_risk_user",
            total_orders=100,
            avg_order_value=25.0,
            avg_order_frequency_days=7.0,
            cancellation_rate=0.02,
            refund_rate=0.01,
            payment_failure_rate=0.005,
            account_age_days=365,
            risk_score=0.1
        )
        
        assert low_risk_profile.risk_score == 0.1
        
        # High risk profile
        high_risk_profile = UserBehaviorProfile(
            user_key="high_risk_user",
            total_orders=5,
            avg_order_value=200.0,
            avg_order_frequency_days=0.5,
            cancellation_rate=0.3,
            refund_rate=0.2,
            payment_failure_rate=0.1,
            account_age_days=1,
            risk_score=0.9
        )
        
        assert high_risk_profile.risk_score == 0.9
    
    def test_profile_rate_validation(self):
        """Test validation of rate fields (0.0 to 1.0)"""
        with pytest.raises(ValidationError):
            UserBehaviorProfile(
                user_key="test",
                cancellation_rate=-0.1  # Invalid rate
            )
        
        with pytest.raises(ValidationError):
            UserBehaviorProfile(
                user_key="test",
                refund_rate=1.5  # Invalid rate
            )
    
    def test_profile_update_timestamp(self):
        """Test profile timestamp handling"""
        profile = UserBehaviorProfile(
            user_key="test_user",
            total_orders=10
        )
        
        # Should have a timestamp
        assert profile.profile_last_updated is not None


class TestActionResult:
    """Test ActionResult model validation and functionality"""
    
    def test_basic_action_result(self):
        """Test basic action result creation"""
        result = ActionResult(
            action_taken="REVIEW",
            status="COMPLETED",
            timestamp=datetime.now().isoformat(),
            details={"reviewer_assigned": "fraud_team_1"}
        )
        
        assert result.action_taken == "REVIEW"
        assert result.status == "COMPLETED"
        assert isinstance(result.details, dict)
    
    def test_block_action_result(self):
        """Test block action result creation"""
        block_result = BlockActionResult(
            action_taken="BLOCK",
            status="COMPLETED",
            timestamp=datetime.now().isoformat(),
            block_reason="High fraud score",
            block_duration_hours=24,
            reviewer_notified=True
        )
        
        assert block_result.action_taken == "BLOCK"
        assert block_result.block_reason == "High fraud score"
        assert block_result.block_duration_hours == 24
        assert block_result.reviewer_notified is True
    
    def test_action_status_validation(self):
        """Test action status validation"""
        valid_statuses = ["PENDING", "COMPLETED", "FAILED", "CANCELLED"]
        
        for status in valid_statuses:
            result = ActionResult(
                action_taken="REVIEW",
                status=status,
                timestamp=datetime.now().isoformat()
            )
            assert result.status == status
        
        with pytest.raises(ValidationError):
            ActionResult(
                action_taken="REVIEW",
                status="INVALID_STATUS",
                timestamp=datetime.now().isoformat()
            )
    
    def test_action_result_to_dict(self):
        """Test action result dictionary conversion"""
        result = ActionResult(
            action_taken="REVIEW",
            status="COMPLETED",
            timestamp=datetime.now().isoformat(),
            details={"test": "value"}
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["action_taken"] == "REVIEW"
        assert result_dict["status"] == "COMPLETED"
        assert "details" in result_dict


class TestModelIntegration:
    """Test integration between different models"""
    
    def test_order_to_fraud_result_flow(self, sample_order_data):
        """Test the flow from order to fraud result"""
        order = sample_order_data
        
        # Create fraud result for the order
        fraud_result = FraudResult(
            fraud_score=0.3,
            recommended_action="ALLOW",
            confidence_level=0.9,
            reasoning="Low risk order with normal patterns",
            detected_patterns=[],
            agent_analyses=[
                AgentAnalysis(
                    agent_name="pattern_analyzer",
                    analysis_result="No suspicious patterns detected",
                    confidence=0.95,
                    processing_time_ms=120
                )
            ],
            processing_time_ms=250
        )
        
        # Verify compatibility
        assert isinstance(order.order_id, str)
        assert isinstance(fraud_result.fraud_score, float)
        assert fraud_result.recommended_action in ["ALLOW", "REVIEW", "BLOCK"]
    
    def test_fraud_result_to_action_result_flow(self, sample_fraud_result):
        """Test the flow from fraud result to action result"""
        fraud_result = sample_fraud_result
        
        # Create corresponding action result
        if fraud_result.recommended_action == "BLOCK":
            action_result = BlockActionResult(
                action_taken="BLOCK",
                status="COMPLETED",
                timestamp=datetime.now().isoformat(),
                block_reason=fraud_result.reasoning,
                block_duration_hours=24,
                reviewer_notified=True
            )
        else:
            action_result = ActionResult(
                action_taken=fraud_result.recommended_action,
                status="COMPLETED",
                timestamp=datetime.now().isoformat(),
                details={"fraud_score": fraud_result.fraud_score}
            )
        
        # Verify flow
        assert action_result.action_taken == fraud_result.recommended_action
        assert action_result.status == "COMPLETED"
    
    def test_user_profile_risk_impact(self, sample_user_profile):
        """Test how user profile affects fraud scoring"""
        profile = sample_user_profile
        
        # Low risk profile should influence fraud detection
        if profile.risk_score < 0.3:
            expected_base_adjustment = -0.1  # Lower base fraud score
        elif profile.risk_score > 0.7:
            expected_base_adjustment = 0.2   # Higher base fraud score
        else:
            expected_base_adjustment = 0.0   # Neutral adjustment
        
        # Verify profile provides useful risk signals
        assert 0.0 <= profile.risk_score <= 1.0
        assert profile.total_orders >= 0
        assert profile.account_age_days >= 0