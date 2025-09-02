#!/usr/bin/env python3
"""
Setup script to download required Spark JAR files for Kafka integration
"""

import os
import sys
import subprocess
import requests
from pathlib import Path

def download_jar(url: str, output_path: str) -> bool:
    """Download JAR file from URL"""
    try:
        print(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")
        return False

def setup_spark_kafka_jars():
    """Setup Spark Kafka JARs"""
    
    # Create jars directory
    jars_dir = Path("jars")
    jars_dir.mkdir(exist_ok=True)
    
    # Get PySpark version and determine compatible Kafka connector version
    try:
        import pyspark
        pyspark_version = pyspark.__version__
        print(f"📋 Detected PySpark version: {pyspark_version}")
    except ImportError:
        print("⚠️  PySpark not found, using default version")
        pyspark_version = "3.5.6"
    
    # Use latest stable Kafka connector version compatible with PySpark
    if pyspark_version.startswith('4.'):
        # PySpark 4.0 is too new - use latest 3.5.x Kafka connector
        kafka_version = "3.5.6"
        kafka_clients_version = "3.4.1"
        print(f"⚠️  PySpark 4.0.0 detected - using Spark 3.5.6 Kafka connector (backwards compatible)")
    elif pyspark_version.startswith('3.5'):
        kafka_version = pyspark_version
        kafka_clients_version = "3.4.1"
    elif pyspark_version.startswith('3.4'):
        kafka_version = pyspark_version  
        kafka_clients_version = "3.3.2"
    else:
        kafka_version = "3.5.6"  # fallback to latest stable
        kafka_clients_version = "3.4.1"
    
    print(f"📦 Using Kafka connector version: {kafka_version}")
    
    # Updated JARs with correct versions
    jars_to_download = [
        {
            "name": f"spark-sql-kafka-0-10_2.12-{kafka_version}.jar",
            "url": f"https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/{kafka_version}/spark-sql-kafka-0-10_2.12-{kafka_version}.jar"
        },
        {
            "name": f"kafka-clients-{kafka_clients_version}.jar", 
            "url": f"https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/{kafka_clients_version}/kafka-clients-{kafka_clients_version}.jar"
        },
        {
            "name": "spark-token-provider-kafka-0-10_2.12-{}.jar".format(kafka_version),
            "url": f"https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/{kafka_version}/spark-token-provider-kafka-0-10_2.12-{kafka_version}.jar"
        }
    ]
    
    print("🔽 Downloading Spark Kafka JAR dependencies...")
    print("=" * 60)
    
    success_count = 0
    for jar_info in jars_to_download:
        jar_path = jars_dir / jar_info["name"]
        
        if jar_path.exists():
            print(f"⚠️  Already exists: {jar_path}")
            success_count += 1
            continue
            
        if download_jar(jar_info["url"], str(jar_path)):
            success_count += 1
    
    print("=" * 60)
    print(f"📊 Download Summary: {success_count}/{len(jars_to_download)} JARs downloaded")
    
    if success_count == len(jars_to_download):
        print("✅ All Spark Kafka JARs downloaded successfully!")
        print("\n📝 Next steps:")
        print("1. Install Java 17+:")
        print("   brew install openjdk@17")
        print("   export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home")
        print("\n2. Set JAR path in environment:")
        print(f"   export SPARK_JARS={jars_dir.absolute()}/*.jar")
        print("\n3. Restart the fraud detection system:")
        print("   ./start_dev.sh")
        
        # Create environment setup script
        setup_script = """#!/bin/bash
# Spark JAR setup for fraud detection system

export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SPARK_JARS=$(pwd)/jars/*.jar

echo "✅ Spark environment configured"
echo "Java version: $(java -version 2>&1 | head -1)"
echo "Spark JARs: $SPARK_JARS"
"""
        
        with open("setup_spark_env.sh", "w") as f:
            f.write(setup_script)
        
        os.chmod("setup_spark_env.sh", 0o755)
        print(f"\n📜 Created setup script: setup_spark_env.sh")
        
    else:
        print("❌ Some JARs failed to download. Please check your internet connection.")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Spark Kafka JAR Setup")
    print("=" * 60)
    
    try:
        if setup_spark_kafka_jars():
            print("\n🎉 Setup completed successfully!")
        else:
            print("\n💥 Setup failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)