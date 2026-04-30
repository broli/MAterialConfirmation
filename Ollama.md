# 🧠 Ollama Integration & Local AI

## What is Ollama?
[Ollama](https://ollama.com/) is a lightweight, open-source framework that allows you to run large language models (LLMs) locally on your own machine. It handles the complexities of GPU acceleration, model management, and provides a simple REST API that our application consumes.

## Why we use it
The PKB Material Confirmation System uses local AI for several critical reasons:
1. **Data Privacy:** Contracts and client data never leave your local network. Everything is processed on your machine.
2. **Cost Efficiency:** There are no per-token fees or subscriptions required to run the matching engine.
3. **Reliability:** The system works entirely offline (once models are downloaded), making it resilient to internet outages.
4. **Customization:** We can switch between different models (Llama 3, Qwen, etc.) depending on the task's complexity vs. speed requirements.

## How it's integrated
We have a deep integration with Ollama through the `ollama_utils.py` module:
- **Lifecycle Management:** The app can automatically detect if Ollama is installed, start the background service, and even kill the process to free up system memory when the app closes.
- **REST API:** We communicate with Ollama via its local endpoint (`http://localhost:11434`).
- **In-App Management:** You can pull new models, delete old ones, and select which model to use directly from the **Settings** menu.

## Recommended Models
While the system is model-agnostic, we recommend the following for the best balance of accuracy and performance:
- **llama3.1 (8b):** The current gold standard for extraction and reasoning.
- **qwen2 (7b):** Excellent performance on structured data tasks.
- **qwen2:0.5b:** Use this if you have a very old machine and only need basic keyword extraction.

## Troubleshooting
If you encounter errors like `Model not found`, open the **Settings** menu in the app and ensures you have pulled the model you've selected in the dropdown.
