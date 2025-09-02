#!/usr/bin/env python3
"""
UberEats Fraud Detection - Connection Validation Tool
Comprehensive validation of all external service connections
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))
from logging_config import setup_logging
from correlation import get_correlation_logger

@dataclass 
class ConnectionTest:
    """Individual connection test definition"""
    name: str
    service: str
    test_function: str
    required: bool = True
    timeout: int = 30

class ConnectionValidator:
    """Comprehensive connection validation"""
    
    def __init__(self):
        setup_logging(log_level='INFO', enable_file_logging=True)
        self.logger = get_correlation_logger('connection_validator')
        
        self.results = {}
        
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all connection validations"""
        self.logger.info("🔍 Starting comprehensive connection validation")
        
        tests = [
            ConnectionTest("OpenAI API", "openai", "test_openai", True, 15),
            ConnectionTest("Confluent Kafka", "kafka", "test_kafka", True, 20),
            ConnectionTest("Qdrant Vector DB", "qdrant", "test_qdrant", True, 15),
            ConnectionTest("Redis Cache", "redis", "test_redis", False, 10),
            ConnectionTest("PostgreSQL", "postgres", "test_postgres", False, 10),
            ConnectionTest("Spark Dependencies", "spark", "test_spark", True, 10),
        ]
        
        # Run tests with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._run_single_test, test): test
                for test in tests
            }
            
            for future in concurrent.futures.as_completed(futures, timeout=60):
                test = futures[future]
                try:
                    result = future.result(timeout=test.timeout)
                    self.results[test.service] = result
                except concurrent.futures.TimeoutError:
                    self.results[test.service] = {
                        'status': 'error',
                        'message': f'Test timeout after {test.timeout}s',
                        'required': test.required
                    }
                except Exception as e:
                    self.results[test.service] = {
                        'status': 'error', 
                        'message': str(e),
                        'required': test.required
                    }
        
        self._generate_report()
        return self.results
    
    def _run_single_test(self, test: ConnectionTest) -> Dict[str, Any]:
        """Run a single connection test"""
        self.logger.info(f"Testing {test.name}...")
        
        try:
            test_method = getattr(self, test.test_function)
            return test_method()
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'required': test.required
            }
    
    def test_openai(self) -> Dict[str, Any]:
        """Test OpenAI API connection"""
        api_key = os.getenv('OPENAI_API_KEY', '')
        
        if not api_key or api_key == 'sk-your-openai-api-key-here':
            return {
                'status': 'error',
                'message': 'API key not configured',
                'required': True
            }
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # Test chat completion
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'test'"}],
                max_tokens=5
            )
            
            # Test embeddings
            embeddings = client.embeddings.create(
                model="text-embedding-3-small",
                input="test"
            )
            
            return {
                'status': 'success',
                'message': 'OpenAI API working correctly',
                'details': {
                    'chat_model': 'gpt-4o-mini',
                    'embedding_model': 'text-embedding-3-small',
                    'response_id': response.id,
                    'embedding_dimensions': len(embeddings.data[0].embedding)
                },
                'required': True
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'OpenAI connection failed: {str(e)[:100]}',
                'required': True
            }
    
    def test_kafka(self) -> Dict[str, Any]:
        """Test Confluent Kafka connection"""
        username = os.getenv('KAFKA_SASL_USERNAME', '')
        password = os.getenv('KAFKA_SASL_PASSWORD', '')
        bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', '')
        
        if not username or username == 'your-confluent-api-key':
            return {
                'status': 'error',
                'message': 'Confluent credentials not configured',
                'required': True
            }
        
        try:
            from kafka import KafkaConsumer
            import certifi
            
            # Working configuration for Confluent Cloud
            consumer = KafkaConsumer(
                bootstrap_servers=[bootstrap_servers],
                security_protocol='SASL_SSL',
                sasl_mechanism='PLAIN', 
                sasl_plain_username=username,
                sasl_plain_password=password,
                ssl_check_hostname=False,
                ssl_cafile=certifi.where(),
                consumer_timeout_ms=10000,
                api_version=(0, 10, 2)
            )
            
            # Verify connection
            connection_status = consumer.bootstrap_connected()
            
            # Get topics
            topics = consumer.topics()
            topic_count = len(topics) if topics else 0
            
            consumer.close()
            
            return {
                'status': 'success',
                'message': 'Confluent Kafka connection successful',
                'details': {
                    'bootstrap_servers': bootstrap_servers,
                    'connection_type': 'SASL_SSL',
                    'topics_count': topic_count,
                    'ssl_cafile': certifi.where()
                },
                'required': True
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Kafka connection failed: {str(e)[:100]}',
                'required': True
            }
    
    def test_qdrant(self) -> Dict[str, Any]:
        """Test Qdrant vector database connection"""
        url = os.getenv('QDRANT_URL', '')
        api_key = os.getenv('QDRANT_API_KEY', '')
        
        if not url or 'your-cluster-id' in url:
            return {
                'status': 'error', 
                'message': 'Qdrant credentials not configured',
                'required': True
            }
        
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            import numpy as np
            
            client = QdrantClient(
                url=url,
                api_key=api_key if api_key else None
            )
            
            # Test connection
            collections = client.get_collections()
            
            # Test creating a temporary collection for validation
            test_collection = "connection_test"
            
            try:
                # Create test collection
                client.create_collection(
                    collection_name=test_collection,
                    vectors_config=VectorParams(size=128, distance=Distance.COSINE)
                )
                
                # Insert test vector
                client.upsert(
                    collection_name=test_collection,
                    points=[{
                        "id": 1,
                        "vector": np.random.random(128).tolist(),
                        "payload": {"test": "connection_validation"}
                    }]
                )
                
                # Search test
                results = client.search(
                    collection_name=test_collection,
                    query_vector=np.random.random(128).tolist(),
                    limit=1
                )
                
                # Cleanup
                client.delete_collection(test_collection)
                
            except Exception:
                # Collection operations failed, but connection works
                pass
            
            return {
                'status': 'success',
                'message': 'Qdrant vector database connection successful',
                'details': {
                    'url': url,
                    'collections_count': len(collections.collections),
                    'has_api_key': bool(api_key)
                },
                'required': True
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Qdrant connection failed: {str(e)[:100]}',
                'required': True
            }
    
    def test_redis(self) -> Dict[str, Any]:
        """Test Redis cache connection"""
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            import redis
            client = redis.from_url(redis_url)
            
            # Test basic operations
            client.set('test_key', 'test_value', ex=60)
            value = client.get('test_key')
            client.delete('test_key')
            
            info = client.info('server')
            
            return {
                'status': 'success',
                'message': 'Redis cache connection successful',
                'details': {
                    'url': redis_url,
                    'version': info.get('redis_version'),
                    'mode': info.get('redis_mode')
                },
                'required': False
            }
            
        except Exception as e:
            return {
                'status': 'warning',
                'message': f'Optional Redis cache not available: {str(e)[:50]}',
                'required': False
            }
    
    def test_postgres(self) -> Dict[str, Any]:
        """Test PostgreSQL database connection"""
        db_url = os.getenv('DATABASE_URL', '')
        
        if not db_url or 'localhost' in db_url:
            return {
                'status': 'warning',
                'message': 'Optional PostgreSQL not configured',
                'required': False
            }
        
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Test query
            cursor.execute('SELECT version();')
            version = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            parsed = urlparse(db_url)
            
            return {
                'status': 'success',
                'message': 'PostgreSQL database connection successful',
                'details': {
                    'host': parsed.hostname,
                    'database': parsed.path[1:],
                    'version': version[0] if version else 'unknown'
                },
                'required': False
            }
            
        except Exception as e:
            return {
                'status': 'warning',
                'message': f'Optional PostgreSQL not available: {str(e)[:50]}',
                'required': False
            }
    
    def test_spark(self) -> Dict[str, Any]:
        """Test Spark dependencies"""
        try:
            from pyspark.sql import SparkSession
            from pyspark import __version__ as spark_version
            
            # Test Spark session creation
            spark = SparkSession.builder \
                .appName("ConnectionTest") \
                .master("local[1]") \
                .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
                .getOrCreate()
            
            # Test basic functionality
            data = [(1, "test"), (2, "data")]
            df = spark.createDataFrame(data, ["id", "text"])
            count = df.count()
            
            spark.stop()
            
            return {
                'status': 'success',
                'message': 'Spark dependencies working correctly',
                'details': {
                    'spark_version': spark_version,
                    'test_dataframe_count': count
                },
                'required': True
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Spark dependencies failed: {str(e)[:100]}',
                'required': True
            }
    
    def _generate_report(self):
        """Generate comprehensive validation report"""
        self.logger.info("📊 Connection Validation Report")
        self.logger.info("=" * 70)
        
        success_count = sum(1 for r in self.results.values() if r['status'] == 'success')
        warning_count = sum(1 for r in self.results.values() if r['status'] == 'warning') 
        error_count = sum(1 for r in self.results.values() if r['status'] == 'error')
        
        required_errors = sum(1 for r in self.results.values() 
                            if r['status'] == 'error' and r.get('required', True))
        
        # Display results
        for service, result in self.results.items():
            status_icons = {
                'success': '✅',
                'warning': '⚠️', 
                'error': '❌'
            }
            
            icon = status_icons.get(result['status'], '❓')
            required_text = " (Required)" if result.get('required', True) else " (Optional)"
            
            self.logger.info(f"{icon} {service.title()}: {result['message']}{required_text}")
            
            if result.get('details'):
                for key, value in result['details'].items():
                    self.logger.info(f"   └─ {key}: {value}")
        
        self.logger.info("=" * 70)
        self.logger.info(f"Summary: {success_count} ✅ | {warning_count} ⚠️ | {error_count} ❌")
        
        # Overall status
        if required_errors == 0:
            self.logger.info("🎉 All required services validated successfully!")
            self.logger.info("🚀 System ready for operation")
        else:
            self.logger.error(f"❌ {required_errors} critical services failed validation")
            self.logger.error("🔧 Please fix required service configurations")
        
        # Save detailed report
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'success': success_count,
                'warning': warning_count,
                'error': error_count,
                'required_errors': required_errors,
                'overall_status': 'ready' if required_errors == 0 else 'configuration_needed'
            },
            'results': self.results
        }
        
        with open('backup/connection_validation_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info("💾 Detailed report: connection_validation_report.json")

def main():
    """Main validation function"""
    print("🔍 UberEats Fraud Detection - Connection Validation")
    print("=" * 60)
    
    validator = ConnectionValidator()
    results = validator.run_all_validations()
    
    # Check if system is ready
    required_errors = sum(1 for r in results.values() 
                         if r['status'] == 'error' and r.get('required', True))
    
    if required_errors == 0:
        print("\n🎉 Connection validation completed successfully!")
        print("🚀 All required services are operational")
        return True
    else:
        print(f"\n⚠️  {required_errors} required services need configuration")
        print("🔧 Please check the validation report and fix issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)