import requests
from openai import OpenAI
import instructor
from schema.contract_item import ContractItem

class LocalLLMClient:
    """
    A lightweight wrapper for interacting with a localized Ollama instance,
    now powered by Pydantic and Instructor for deterministic structured outputs.
    """
    def __init__(self, host="http://localhost:11434", model="llama3", log_callback=None):
        self.host = host
        self.model = model
        self.log_callback = log_callback
        
        # Initialize Instructor-patched OpenAI client pointing to Ollama's local endpoint
        self.client = instructor.from_openai(
            OpenAI(
                base_url=f"{self.host}/v1",
                api_key="ollama"  # Required by OpenAI client, but ignored by Ollama
            ),
            mode=instructor.Mode.JSON  # JSON mode
        )

    def _log(self, msg: str):
        if self.log_callback:
            self.log_callback(msg)

    def check_connection(self) -> bool:
        """
        Verify that the Ollama service is running and the model is available.
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=3)
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]
                if not any(m.startswith(self.model) for m in models):
                    return False, f"Model '{self.model}' not found in Ollama."
                return True, "Connected successfully."
            return False, f"Status code {response.status_code}."
        except requests.exceptions.RequestException as e:
            return False, f"Connection failed: {e}"

    def extract_product_fields(self, raw_text: str) -> ContractItem:
        """
        Takes raw messy PDF text and parses out the structured product format
        using Instructor and Pydantic. Returns a ContractItem object.
        """
        system_msg = (
            "You are a strict data extraction AI. "
            "Identify the product category, base item, brand, finish, and dimensions from the text. "
            "IMPORTANT: Return the JSON object directly. DO NOT wrap the response in a 'properties' key or any other root-level key. "
            "Example of CORRECT output: {\"category\": \"...\", \"base_item\": \"...\", ...}"
        )
        
        self._log(f">\n> --- SENDING REQUEST TO OLLAMA (Instructor) ---\n> MODEL: {self.model}\n> RAW TEXT:\n{raw_text}\n> -----------------------------------")
        
        try:
            # Instructor automatically handles parsing the LLM output into the ContractItem Pydantic model
            # and will automatically retry if the LLM makes a formatting mistake.
            result = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"Extract structural information from this raw text string:\n\n\"{raw_text}\""}
                ],
                response_model=ContractItem,
                max_retries=2
            )
            
            self._log(f"<\n< --- RESPONSE FROM OLLAMA ---\n{result.model_dump_json(indent=2)}\n< -----------------------------------\n")
            return result
            
        except Exception as e:
            self._log(f"<\n< --- OLLAMA ERROR ---\n{str(e)}\n< -----------------------------------\n")
            raise RuntimeError(f"Ollama Extraction Error: {e}")

if __name__ == "__main__":
    # Quick self-test logic
    print("Testing connection to Ollama...")
    llm = LocalLLMClient(model="llama3")
    
    success, msg = llm.check_connection()
    if success:
        print("Connected! Testing extraction...")
        try:
            test_str = 'Bath Accessories Grab Bars Traditional 16" Traditional Grab Bar Matte Black'
            res = llm.extract_product_fields(test_str)
            print(f"Extraction successful: {res}")
            print(f"Base Item: {res.base_item}")
            print(f"Dimensions: {res.dimensions}")
        except Exception as e:
            print(f"Test failed during LLM call: {e}")
    else:
        print(f"Ollama Connection Failed: {msg}")
        print("Please ensure Ollama is running and the model is pulled ('ollama run llama3').")
