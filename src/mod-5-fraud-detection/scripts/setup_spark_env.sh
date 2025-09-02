#!/bin/bash
# Spark JAR setup for fraud detection system

export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SPARK_JARS=$(pwd)/jars/*.jar

echo "✅ Spark environment configured"
echo "Java version: $(java -version 2>&1 | head -1)"
echo "Spark JARs: $SPARK_JARS"
