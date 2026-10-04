import json
import time
from typing import Dict, Any, Tuple
import ollama

TEST_CASES = [
    {
        "id": "CASE_1_ELECTRICAL_SIZING",
        "category": "Electrical Protection & Circuit Sizing",
        "instruction": "Calculate electrical safety metrics and circuit protection requirements for the specified compressor model. Provide contactor rating, breaker rating (MOCP), and LRA constraints.",
        "input": "Compressor Model: YA147K1E-TFD-ERZ | Electrical System: 460/380-420 V, 3-Phase, 50/60 Hz"
    },
    {
        "id": "CASE_2_PARAMETRIC_SELECTION",
        "category": "Parametric Model Selection",
        "instruction": "Select the appropriate Copeland compressor model matching the required cooling capacity, refrigerant specification, and electrical supply. Return performance metrics in structured JSON.",
        "input": "Design Requirements: Capacity Target = ~147,000 BTU/hr | Refrigerant = R-454B | Application = Air Conditioning | Electrical = 460/380-420 V, 3 Ph, 50/60 Hz"
    },
    {
        "id": "CASE_3_NOMENCLATURE_DECOMPOSITION",
        "category": "Nomenclature Parsing & Bill of Materials",
        "instruction": "Deconstruct the Copeland compressor model number into engineering specifications. Extract series, capacity multiplier, electrical code, and protection configuration.",
        "input": "Compressor Model: ZP54K5E-TF5-830"
    },
    {
        "id": "CASE_4_MECHANICAL_INTERFACE",
        "category": "Physical Envelope & Mechanical Ports",
        "instruction": "Determine the physical mounting dimensions, stub tube line connections (suction/discharge), and oil charge requirements for the target compressor.",
        "input": "Target Model: ZP31K5E-PFV-830"
    }
]

def query_model(model_name: str, instruction: str, user_input: str) -> Tuple[str, float, bool]:
    prompt = f"{instruction}\n{user_input}"
    start = time.perf_counter()
    
    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "You are a specialized mechanical specification and electrical sizing assistant. Respond strictly in valid JSON."
            },
            {"role": "user", "content": prompt}
        ],
        options={"temperature": 0.1}
    )
    elapsed = time.perf_counter() - start
    content = response["message"]["content"].strip()
    
    # Check strict JSON validity
    is_valid_json = False
    try:
        json.loads(content)
        is_valid_json = True
    except json.JSONDecodeError:
        pass
        
    return content, elapsed, is_valid_json

def run_benchmark():
    models = ["qwen2.5:3b", "spec-adapter"]
    results = []

    print("=" * 80)
    print("RUNNING BENCHMARK: Qwen2.5-3B (Base) vs Spec-Adapter (Fine-Tuned)")
    print("=" * 80)

    for case in TEST_CASES:
        print(f"\n[Test ID: {case['id']}] - {case['category']}")
        print(f"Input: {case['input']}")
        print("-" * 80)
        
        case_data = {"id": case["id"], "category": case["category"], "runs": {}}

        for model in models:
            raw_text, latency, valid_json = query_model(model, case["instruction"], case["input"])
            case_data["runs"][model] = {
                "latency_sec": round(latency, 2),
                "is_valid_json": valid_json,
                "output": raw_text
            }
            
            status = "PASS (Valid JSON)" if valid_json else "FAIL (Invalid / Markdown / Text)"
            print(f"Model: {model:<15} | Latency: {latency:.2f}s | Schema: {status}")
            print(f"Output:\n{raw_text}\n")
        
        results.append(case_data)

    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("=" * 80)
    print("Benchmark complete. Raw logs saved to benchmark_results.json")

if __name__ == "__main__":
    run_benchmark()