import sys
import os
sys.path.append(os.getcwd())
from llm_service import LocalLLMClient

client = LocalLLMClient(model=None)

test_product = {
    'category': 'Faucet',
    'brand': 'Moen',
    'finish': 'Brushed Gold',
    'dimensions': {'Spout Height': '8inch'},
    'description': 'Align 1-Handle Faucet'
}

print("Testing rule compilation for Faucet...")
rules = client.compile_matching_rules(test_product)
print(f"Rules generated: {rules}")
