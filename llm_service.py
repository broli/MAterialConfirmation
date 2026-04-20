import requests
import json
import ast

class LocalLLMClient:
    """
    A lightweight wrapper for interacting with a localized Ollama instance.
    Uses 'llama3' by default as a strong, fast, local extraction model.
    """
    def __init__(self, host="http://localhost:11434", model="llama3", log_callback=None):
        self.host = host
        self.model = model
        self.api_url = f"{self.host}/api/generate"
        self.log_callback = log_callback

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

    def _query_ollama(self, prompt: str, system_message: str = "") -> str:
        """
        Internal function to dispatch a prompt to Ollama.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_message,
            "stream": False,
            "options": {
                "temperature": 0.1 # Keep it deterministic for JSON extraction
            }
        }
        
        try:
            self._log(f">\n> --- SENDING REQUEST TO OLLAMA ---\n> MODEL: {self.model}\n> PROMPT:\n{prompt}\n> -----------------------------------")
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            raw_res = data.get("response", "").strip()
            self._log(f"<\n< --- RESPONSE FROM OLLAMA ---\n{raw_res}\n< -----------------------------------\n")
            return raw_res
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama API Error: {e}")

    def _parse_json_safely(self, text: str) -> dict:
        """
        Extracts JSON from an LLM response, handling common markdown formatting blocks
        and conversational wrappers.
        """
        import re

        # First, try to extract inside markdown blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        else:
            # If no markdown blocks, try to find the outermost curly braces
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                # Fallback to AST literal eval if the LLM output single quotes
                return ast.literal_eval(text)
            except (ValueError, SyntaxError):
                raise ValueError(f"Failed to parse LLM output as JSON:\n{text}")

    def extract_product_fields(self, raw_text: str) -> dict:
        """
        Takes raw messy PDF text and parses out the structured product format.
        """
        system_msg = (
            "You are a strict data extraction AI for a plumbing/bathroom installation catalog. "
            "You will be given a messy text string from a PDF estimate. "
            "Your job is to identify the underlying product and return ONLY a valid JSON object. "
            "Extract these fields: 'category' (e.g. Grab Bar, Faucet), 'brand' (e.g. Moen, Generic), "
            "'finish' (e.g. Matte Black, Chrome), 'dimensions' (a dictionary of width/height/depth if present), "
            "and 'description' (a clean marketing phrase)."
        )
        
        prompt = (
            f"Extract structural information from this raw text string:\n\n\"{raw_text}\"\n\n"
            "Return only valid JSON in this format (leave fields empty string if unknown):\n"
            "{\n"
            "  \"category\": \"...\",\n"
            "  \"brand\": \"...\",\n"
            "  \"finish\": \"...\",\n"
            "  \"dimensions\": {\"width\": \"...\", \"height\": \"...\", \"depth\": \"...\"},\n"
            "  \"description\": \"...\"\n"
            "}"
        )
        
        raw_response = self._query_ollama(prompt, system_msg)
        return self._parse_json_safely(raw_response)

    def compile_matching_rules(self, product_dict: dict) -> dict:
        """
        Generates deterministic matching rules based on a polished product dictionary.
        This provides the regex instructions the MatchingEngine uses to strictly filter.
        """
        system_msg = (
            "You are to generate strict Python regex patterns to identify a plumbing product from a string. "
            "You must ensure that colors (e.g., Matte Black vs Chrome) and sizes (e.g. 16 vs 12) never cross-match. "
            "Return ONLY valid JSON."
        )
        
        prompt = (
            f"Here is the product dictionary:\n{json.dumps(product_dict, indent=2)}\n\n"
            "Generate JSON with three keys:\n"
            "1. 'must_contain_regex': a list of regex strings that MUST be found in a raw PDF text for it to be a match. "
            "Include variations (e.g., for 12 inches: \"12\\\\s*(in|inch|\\\")\"). "
            "Ensure the finish (color) has its synonyms included.\n\n"
            "2. 'must_not_contain_regex': a list of regex strings. If ANY of these are found, it is an instant failure. "
            "For example, if the finish is Matte Black, forbid 'chrome', 'brushed nickel'. "
            "If the size is 12, forbid '16', '18', '24'.\n\n"
            "3. 'keywords': A list of 3-5 important words for fuzzy fallback.\n\n"
            "Return JSON format exactly:\n"
            "{\n"
            "  \"must_contain_regex\": [\"...\"],\n"
            "  \"must_not_contain_regex\": [\"...\"],\n"
            "  \"keywords\": [\"...\"]\n"
            "}"
        )
        
        raw_response = self._query_ollama(prompt, system_msg)
        return self._parse_json_safely(raw_response)

if __name__ == "__main__":
    # Quick self-test logic
    print("Testing connection to Ollama...")
    client = LocalLLMClient(model="llama3")
    
    success, msg = client.check_connection()
    if success:
        print("Connected! Testing extraction...")
        try:
            test_str = 'Bath Accessories Grab Bars Traditional 16" Traditional Grab Bar Matte Black'
            res = client.extract_product_fields(test_str)
            print(f"Extraction successful: {res}")
            
            print("Testing rule compilation...")
            rules = client.compile_matching_rules(res)
            print(f"Rules generated: {rules}")
        except Exception as e:
            print(f"Test failed during LLM call: {e}")
    else:
        print(f"Ollama Connection Failed: {msg}")
        print("Please ensure Ollama is running and the model is pulled ('ollama run llama3').")
