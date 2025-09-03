"""
Knowledge Base Ingestion Script
Run this to populate Qdrant with knowledge from PostgreSQL and MongoDB
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Add src directory to path
sys.path.append(str(project_root / "src"))

from rag.database_rag_loader import DatabaseRAGLoader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main ingestion function"""
    print("🚀 UberEats Knowledge Base Ingestion")
    print("=" * 50)
    
    # Initialize the RAG loader
    rag_loader = DatabaseRAGLoader()
    
    try:
        print("📊 Starting knowledge base ingestion...")
        success = await rag_loader.load_all_knowledge()
        
        if success:
            print("\n✅ Knowledge base ingestion completed successfully!")
            print("\n🎯 Summary:")
            print("- All database connections tested")
            print("- Knowledge extracted from PostgreSQL and MongoDB")
            print("- Documents embedded and stored in Qdrant")
            print("- RAG system ready for agent queries")
            
            print("\n🚀 Next steps:")
            print("1. Test the RAG agents with sample queries")
            print("2. Set up real-time sync for live data updates")
            print("3. Monitor agent performance and response quality")
        else:
            print("\n❌ Knowledge base ingestion failed!")
            print("Check the logs above for specific error details.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Critical error during ingestion: {e}")
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())