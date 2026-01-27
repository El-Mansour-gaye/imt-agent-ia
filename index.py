# BRANCH: feature/m1-rag-core
import argparse
from rag_tools import index_documents

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index IMT data into ChromaDB")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the collection from scratch")
    parser.add_argument("--file", default="imt_data.json", help="JSON file containing the scraped data")
    args = parser.parse_args()

    index_documents(args.file, rebuild=args.rebuild)
