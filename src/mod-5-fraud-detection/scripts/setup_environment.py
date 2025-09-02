#!/usr/bin/env python3
"""
UberEats Fraud Detection System - Environment Setup Script
Phase 1: Complete environment configuration and validation
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import subprocess
from datetime import datetime

# Import our logging system
sys.path.append(str(Path(__file__).parent / 'src'))
from logging_config import setup_logging
from correlation import get_correlation_logger

@dataclass
class ValidationResult:
    """Result of environment validation"""
    service: str
    status: str  # 'success', 'warning', 'error'
    message: str
    details: Optional[Dict[str, Any]] = None

class EnvironmentSetup:
    """Comprehensive environment setup and validation"""
    
    def __init__(self):
        # Initialize logging
        setup_logging(log_level='INFO', enable_file_logging=True)
        self.logger = get_correlation_logger('environment_setup')
        
        self.validation_results: List[ValidationResult] = []
        self.env_file = Path('.env')
        self.template_file = Path('.env.template')
        
    def run_complete_setup(self) -> bool:
        """Run complete Phase 1 environment setup"""
        self.logger.info("🚀 Starting Phase 1: Environment Setup")
        self.logger.info("=" * 60)
        
        try:
            # Step 1: Environment file setup
            if not self._setup_env_file():
                return False
            
            # Step 2: Load and validate environment
            if not self._load_environment():
                return False
            
            # Step 3: Validate all services
            self._validate_all_services()
            
            # Step 4: Setup directories
            self._setup_directories()
            
            # Step 5: Generate setup report
            self._generate_setup_report()
            
            # Step 6: Provide next steps
            self._show_next_steps()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Environment setup failed: {e}")
            return False
    
    def _setup_env_file(self) -> bool:
        """Setup environment file from template"""
        self.logger.info("📝 Setting up environment file...")
        
        if not self.template_file.exists():
            self.logger.error("❌ .env.template file not found!")
            return False
        
        if not self.env_file.exists():
            self.logger.info("📋 Creating .env file from template...")
            
            # Copy template to .env
            with open(self.template_file, 'r') as template:
                content = template.read()
            
            with open(self.env_file, 'w') as env_file:
                env_file.write(content)
            
            self.logger.warning("⚠️  .env file created from template")
            self.logger.warning("🔑 Please edit .env file with your actual credentials:")
            self.logger.warning("   - KAFKA_SASL_USERNAME (Confluent Cloud API Key)")
            self.logger.warning("   - KAFKA_SASL_PASSWORD (Confluent Cloud API Secret)")
            self.logger.warning("   - OPENAI_API_KEY (OpenAI API Key)")
            self.logger.warning("   - QDRANT_URL and QDRANT_API_KEY (Qdrant Cloud)")
            
            return False  # Stop here for user to configure
        
        self.logger.info("✅ .env file exists")
        return True
    
    def _load_environment(self) -> bool:
        """Load environment variables from .env file"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            self.logger.info("✅ Environment variables loaded")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to load environment: {e}")
            return False
    
    def _validate_all_services(self):
        """Validate all external services"""
        self.logger.info("🔍 Validating external services...")
        
        # OpenAI API validation
        self._validate_openai()
        
        # Confluent Cloud Kafka validation
        self._validate_kafka()
        
        # Qdrant validation
        self._validate_qdrant()
        
        # Optional services
        self._validate_redis()
        self._validate_postgres()
    
    def _validate_openai(self):
        """Validate OpenAI API connection"""
        try:
            api_key = os.getenv('OPENAI_API_KEY', '')
            
            if not api_key or api_key == 'sk-your-openai-api-key-here':
                self.validation_results.append(ValidationResult(
                    service='OpenAI',
                    status='error',
                    message='API key not configured'
                ))
                return
            
            # Test OpenAI connection
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                
                # Test with a minimal request
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                
                self.validation_results.append(ValidationResult(
                    service='OpenAI',
                    status='success',
                    message='API connection successful',
                    details={'model': 'gpt-4o-mini', 'response_id': response.id}
                ))
                
            except Exception as e:
                self.validation_results.append(ValidationResult(
                    service='OpenAI',
                    status='error',
                    message=f'API connection failed: {str(e)[:100]}'
                ))
        
        except Exception as e:
            self.validation_results.append(ValidationResult(
                service='OpenAI',
                status='error',
                message=f'Validation error: {e}'
            ))
    
    def _validate_kafka(self):
        """Validate Confluent Cloud Kafka connection"""
        try:
            username = os.getenv('KAFKA_SASL_USERNAME', '')
            password = os.getenv('KAFKA_SASL_PASSWORD', '')
            bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', '')
            
            if not username or username == 'your-confluent-api-key':
                self.validation_results.append(ValidationResult(
                    service='Kafka',
                    status='error',
                    message='Confluent Cloud credentials not configured'
                ))
                return
            
            # Test Kafka connection
            try:
                from kafka import KafkaConsumer
                from kafka.errors import KafkaError
                
                consumer = KafkaConsumer(
                    bootstrap_servers=bootstrap_servers,
                    security_protocol='SASL_SSL',
                    sasl_mechanism='PLAIN',
                    sasl_plain_username=username,
                    sasl_plain_password=password,
                    consumer_timeout_ms=5000
                )
                
                # Get cluster metadata
                metadata = consumer.list_consumer_groups()
                consumer.close()
                
                self.validation_results.append(ValidationResult(
                    service='Kafka',
                    status='success',
                    message='Confluent Cloud connection successful',
                    details={'bootstrap_servers': bootstrap_servers}
                ))
                
            except Exception as e:
                self.validation_results.append(ValidationResult(
                    service='Kafka',
                    status='error',
                    message=f'Connection failed: {str(e)[:100]}'
                ))
        
        except Exception as e:
            self.validation_results.append(ValidationResult(
                service='Kafka',
                status='error',
                message=f'Validation error: {e}'
            ))
    
    def _validate_qdrant(self):
        """Validate Qdrant vector database connection"""
        try:
            url = os.getenv('QDRANT_URL', '')
            api_key = os.getenv('QDRANT_API_KEY', '')
            
            if not url or url == 'https://your-cluster-id.eu-central.aws.cloud.qdrant.io:6333':
                self.validation_results.append(ValidationResult(
                    service='Qdrant',
                    status='error',
                    message='Qdrant Cloud credentials not configured'
                ))
                return
            
            # Test Qdrant connection
            try:
                from qdrant_client import QdrantClient
                
                client = QdrantClient(
                    url=url,
                    api_key=api_key if api_key else None
                )
                
                # Test connection
                collections = client.get_collections()
                
                self.validation_results.append(ValidationResult(
                    service='Qdrant',
                    status='success',
                    message='Vector database connection successful',
                    details={
                        'url': url,
                        'collections_count': len(collections.collections)
                    }
                ))
                
            except Exception as e:
                self.validation_results.append(ValidationResult(
                    service='Qdrant',
                    status='error',
                    message=f'Connection failed: {str(e)[:100]}'
                ))
        
        except Exception as e:
            self.validation_results.append(ValidationResult(
                service='Qdrant',
                status='error',
                message=f'Validation error: {e}'
            ))
    
    def _validate_redis(self):
        """Validate Redis connection (optional)"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            
            try:
                import redis
                client = redis.from_url(redis_url)
                client.ping()
                
                self.validation_results.append(ValidationResult(
                    service='Redis',
                    status='success',
                    message='Cache connection successful',
                    details={'url': redis_url}
                ))
                
            except Exception as e:
                self.validation_results.append(ValidationResult(
                    service='Redis',
                    status='warning',
                    message=f'Optional cache not available: {str(e)[:50]}'
                ))
        
        except Exception as e:
            self.validation_results.append(ValidationResult(
                service='Redis',
                status='warning',
                message='Optional cache validation skipped'
            ))
    
    def _validate_postgres(self):
        """Validate PostgreSQL connection (optional)"""
        try:
            db_url = os.getenv('DATABASE_URL', '')
            
            if not db_url or 'localhost' in db_url:
                self.validation_results.append(ValidationResult(
                    service='PostgreSQL',
                    status='warning',
                    message='Optional database not configured'
                ))
                return
            
            try:
                import psycopg2
                conn = psycopg2.connect(db_url)
                conn.close()
                
                self.validation_results.append(ValidationResult(
                    service='PostgreSQL',
                    status='success',
                    message='Database connection successful'
                ))
                
            except Exception as e:
                self.validation_results.append(ValidationResult(
                    service='PostgreSQL',
                    status='warning',
                    message=f'Optional database not available: {str(e)[:50]}'
                ))
        
        except Exception as e:
            self.validation_results.append(ValidationResult(
                service='PostgreSQL',
                status='warning',
                message='Optional database validation skipped'
            ))
    
    def _setup_directories(self):
        """Create required directories"""
        directories = [
            'logs',
            'checkpoint', 
            'data/cache',
            'tmp/spark-checkpoint',
            'rag/logs',
            'tests/data'
        ]
        
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"✅ Created {len(directories)} required directories")
    
    def _generate_setup_report(self):
        """Generate comprehensive setup report"""
        self.logger.info("📊 Environment Validation Report")
        self.logger.info("=" * 60)
        
        success_count = sum(1 for r in self.validation_results if r.status == 'success')
        warning_count = sum(1 for r in self.validation_results if r.status == 'warning')
        error_count = sum(1 for r in self.validation_results if r.status == 'error')
        
        # Log each result
        for result in self.validation_results:
            if result.status == 'success':
                icon = "✅"
            elif result.status == 'warning':
                icon = "⚠️"
            else:
                icon = "❌"
            
            self.logger.info(f"{icon} {result.service}: {result.message}")
            
            if result.details:
                for key, value in result.details.items():
                    self.logger.info(f"   {key}: {value}")
        
        self.logger.info("=" * 60)
        self.logger.info(f"📈 Summary: {success_count} ✅ | {warning_count} ⚠️ | {error_count} ❌")
        
        # Save report to file
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'success': success_count,
                'warning': warning_count,
                'error': error_count
            },
            'results': [
                {
                    'service': r.service,
                    'status': r.status,
                    'message': r.message,
                    'details': r.details or {}
                } for r in self.validation_results
            ]
        }
        
        with open('backup/environment_validation_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info("💾 Detailed report saved to: environment_validation_report.json")
    
    def _show_next_steps(self):
        """Show next steps based on validation results"""
        self.logger.info("🎯 Next Steps")
        self.logger.info("=" * 60)
        
        # Check critical services
        critical_errors = [r for r in self.validation_results 
                          if r.status == 'error' and r.service in ['OpenAI', 'Kafka', 'Qdrant']]
        
        if critical_errors:
            self.logger.error("❌ Critical services not configured:")
            for error in critical_errors:
                self.logger.error(f"   • {error.service}: {error.message}")
            
            self.logger.info("🔧 Please configure missing credentials in .env file")
            self.logger.info("📖 See .env.template for required variables")
            return
        
        self.logger.info("✅ Core services validated successfully!")
        self.logger.info("🚀 Ready for Phase 2: Data Pipeline Activation")
        self.logger.info("")
        self.logger.info("Next commands to run:")
        self.logger.info("1. Simple Pipeline:   python src/streaming/final_simple_app.py")
        self.logger.info("2. AI Pipeline:       python src/streaming/agentic_spark_app.py")
        self.logger.info("3. Analytics:         streamlit run src/analytics/streamlit_dashboard.py")
        self.logger.info("4. RAG System:        cd rag && astro dev start")

def main():
    """Main setup function"""
    print("🎯 UberEats Fraud Detection - Phase 1: Environment Setup")
    print("=" * 60)
    
    setup = EnvironmentSetup()
    
    if '--validate-only' in sys.argv:
        # Only run validation
        setup._load_environment()
        setup._validate_all_services()
        setup._generate_setup_report()
        setup._show_next_steps()
    else:
        # Run complete setup
        success = setup.run_complete_setup()
        
        if success:
            print("\n🎉 Phase 1 Environment Setup completed successfully!")
        else:
            print("\n⚠️  Environment setup requires configuration.")
            print("Please edit the .env file with your credentials and run again.")

if __name__ == "__main__":
    main()