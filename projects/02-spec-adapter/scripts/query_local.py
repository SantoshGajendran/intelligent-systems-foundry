import json
import ollama

def query_spec_model(instruction: str, specs: str) -> dict:
    prompt = f"{instruction}\n{specs}"
    
    response = ollama.chat(
        model="spec-adapter",
        messages=[
            {"role": "user", "content": prompt}
        ],
        options={
            "temperature": 0.1
        }
    )
    
    raw_content = response["message"]["content"]
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError:
        return {"raw_output": raw_content}

if __name__ == "__main__":
    task = "Select the appropriate Copeland compressor model matching the required cooling capacity, refrigerant specification, and electrical supply. Return performance metrics in structured JSON."
    input_specs = "Design Requirements: Capacity Target = ~147,000 BTU/hr | Refrigerant = R-454B | Application = Air Conditioning | Electrical = 460/380-420 V, 3 Ph, 50/60 Hz"
    
    data = query_spec_model(task, input_specs)
    print(json.dumps(data, indent=2))