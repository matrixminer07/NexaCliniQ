# Test imports to identify issues
print("Testing upgrade module imports...")

try:
    from chembl_integration import fetch_target_id, load_or_fetch_dataset, train_on_chembl
    print("✅ ChEMBL integration imported successfully")
except Exception as e:
    print(f"❌ ChEMBL integration failed: {e}")

try:
    from smiles_pipeline import smiles_to_descriptors, batch_smiles_to_features
    print("✅ SMILES pipeline imported successfully")
except Exception as e:
    print(f"❌ SMILES pipeline failed: {e}")

try:
    from therapeutic_models import predict_ta, compare_all_tas, THERAPEUTIC_AREAS
    print("✅ Therapeutic models imported successfully")
except Exception as e:
    print(f"❌ Therapeutic models failed: {e}")

try:
    from database import log_prediction, get_history, get_stats
    print("✅ Database module imported successfully")
except Exception as e:
    print(f"❌ Database module failed: {e}")

try:
    from active_learning import compute_uncertainty, add_to_queue
    print("✅ Active learning imported successfully")
except Exception as e:
    print(f"❌ Active learning failed: {e}")

try:
    from llm_analyst import retrieve_compound_context, ask_analyst
    print("✅ LLM analyst imported successfully")
except Exception as e:
    print(f"❌ LLM analyst failed: {e}")

try:
    from gnn_model import predict_gnn, train_gnn
    print("✅ GNN model imported successfully")
except Exception as e:
    print(f"❌ GNN model failed: {e}")

print("\nTesting basic dependencies...")

try:
    import requests
    print("✅ requests available")
except Exception as e:
    print(f"❌ requests failed: {e}")

try:
    import pandas as pd
    print("✅ pandas available")
except Exception as e:
    print(f"❌ pandas failed: {e}")

try:
    import numpy as np
    print("✅ numpy available")
except Exception as e:
    print(f"❌ numpy failed: {e}")

try:
    import sqlalchemy
    print("✅ sqlalchemy available")
except Exception as e:
    print(f"❌ sqlalchemy failed: {e}")

try:
    import anthropic
    print("✅ anthropic available")
except Exception as e:
    print(f"❌ anthropic failed: {e}")
