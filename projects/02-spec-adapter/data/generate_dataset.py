import json
import random
from pathlib import Path
import pandas as pd


def clean_val(val, default="N/A"):
    """Clean raw dataframe cell values into JSON-serializable primitives."""
    if pd.isna(val) or val is None:
        return default
    s = str(val).strip()
    if s in ["-", "", "None", "nan"]:
        return default
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def find_catalog_path() -> Path:
    """Resolve file location regardless of current working directory."""
    candidate_paths = [
        Path("projects/02-spec-adapter/data/raw/copeland_compressor_master_summary.xlsx"),
        Path("data/raw/copeland_compressor_master_summary.xlsx"),
        Path("copeland_compressor_master_summary.xlsx"),
        Path("../data/raw/copeland_compressor_master_summary.xlsx")
    ]
    for p in candidate_paths:
        if p.exists():
            return p
    raise FileNotFoundError(
        "Could not locate 'copeland_compressor_master_summary.xlsx'. "
        "Place it in 'projects/02-spec-adapter/data/raw/' or current directory."
    )


def main():
    input_file = find_catalog_path()
    output_dir = input_file.parent.parent / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading master engineering catalog: {input_file}")
    df = pd.read_excel(input_file, sheet_name=0)

    dataset_records = []

    for _, row in df.iterrows():
        # Core identification & operating baseline
        model = str(row["Compressor Model"]).strip()
        comp_type = str(row["Compressor Type"]).strip()
        refrig = str(row["Refrigerant"]).strip()
        voltage = str(row["Voltage (V)"]).strip()
        phase = clean_val(row["Phase (Ph)"], 3)
        freq = str(row["Frequency (Hz)"]).strip()
        application = str(row["Application"]).strip()

        # Performance characteristics
        capacity_btu = clean_val(row["Nominal Capacity (BTU/hr)"], 0)
        power_watts = clean_val(row["Input Power (Watts)"], 0)
        rated_current = clean_val(row["Rated Current (Amps)"], 0.0)
        eer = clean_val(row["EER (BTU/Wh)"], 0.0)
        mass_flow = clean_val(row["Mass Flow (lbs/hr)"], 0)
        disp_cfm = clean_val(row["Displacement (CFM)"], 0.0)
        disp_in3 = clean_val(row["Displacement (in³/rev)"], 0.0)
        speed_rpm = clean_val(row["Rated Speed (RPM)"], 3500)

        # Electrical protection ratings
        lra = clean_val(row["LRA High (Amps)"], 0.0)
        mcc = clean_val(row["MCC (Amps)"], 0.0)
        mop = clean_val(row["Max Operating Current (Amps)"], 0.0)
        rla_contactor = clean_val(row["RLA (MCC / 1.4 Contactor)"], 0.0)
        rla_breaker = clean_val(row["RLA (MCC / 1.56 Breaker)"], 0.0)

        # Physical and mechanical envelope
        suction = clean_val(row["Suction Size"])
        discharge = clean_val(row["Discharge Size"])
        length = clean_val(row["Overall Length (in)"], 0.0)
        width = clean_val(row["Overall Width (in)"], 0.0)
        height = clean_val(row["Overall Height (in)"], 0.0)
        mount_l = clean_val(row["Mounting Length (in)"], 0.0)
        mount_w = clean_val(row["Mounting Width (in)"], 0.0)
        weight_lbs = clean_val(row["Net Weight (lbs)"], 0.0)
        oil_type = clean_val(row["Oil Type"], "RL32-3MAF")
        oil_init_oz = clean_val(row["Initial Oil Charge (oz)"], 0)
        sound_power = clean_val(row["Sound Power (dBA)"], "N/A")

        # ------------------------------------------------------------------
        # Task 1: Parametric Selection & Capacity Sizing
        # ------------------------------------------------------------------
        task_1 = {
            "instruction": (
                "Select the appropriate Copeland compressor model matching the required cooling capacity, "
                "refrigerant specification, and electrical supply. Return performance metrics in structured JSON."
            ),
            "input": (
                f"Design Requirements: Capacity Target = ~{capacity_btu:,} BTU/hr | "
                f"Refrigerant = {refrig} | Application = {application} | "
                f"Electrical = {voltage}, {phase} Ph, {freq}"
            ),
            "output": json.dumps({
                "selected_model": model,
                "compressor_type": comp_type,
                "refrigerant": refrig,
                "nominal_capacity_btu_hr": capacity_btu,
                "input_power_watts": power_watts,
                "eer_btu_wh": eer,
                "mass_flow_lbs_hr": mass_flow,
                "displacement_cfm": disp_cfm,
                "rated_current_amps": rated_current
            }, indent=2)
        }
        dataset_records.append(task_1)

        # ------------------------------------------------------------------
        # Task 2: Electrical Sizing & Circuit Protection Compliance
        # ------------------------------------------------------------------
        task_2 = {
            "instruction": (
                "Calculate electrical safety metrics and circuit protection requirements for the specified compressor model. "
                "Provide contactor rating, breaker rating (MOCP), and LRA constraints."
            ),
            "input": f"Compressor Model: {model} | Electrical System: {voltage}, {phase}-Phase, {freq}",
            "output": json.dumps({
                "compressor_model": model,
                "lra_amps": lra,
                "mcc_amps": mcc,
                "max_operating_current_amps": mop,
                "sizing_compliance": {
                    "rla_contactor_min_amps": rla_contactor,
                    "rla_breaker_mocp_amps": rla_breaker,
                    "standard_rule": "Contactor sized at >= MCC/1.4; Breaker/MOCP sized per MCC/1.56 per NEC Article 440."
                }
            }, indent=2)
        }
        dataset_records.append(task_2)

        # ------------------------------------------------------------------
        # Task 3: Mechanical Envelope, Mounting, & Line Sizing
        # ------------------------------------------------------------------
        task_3 = {
            "instruction": (
                "Retrieve physical dimensions, mounting footprint, weight, and piping connection specs for mechanical installation."
            ),
            "input": f"Verify mechanical dimensions and fittings for model: {model}",
            "output": json.dumps({
                "compressor_model": model,
                "overall_dimensions_inches": {
                    "length": length,
                    "width": width,
                    "height": height
                },
                "mounting_dimensions_inches": {
                    "length": mount_l,
                    "width": mount_w
                },
                "line_connections": {
                    "suction_fitting": suction,
                    "discharge_fitting": discharge
                },
                "lubrication": {
                    "oil_type": oil_type,
                    "initial_charge_oz": oil_init_oz
                },
                "net_weight_lbs": weight_lbs,
                "sound_power_dba": sound_power
            }, indent=2)
        }
        dataset_records.append(task_3)

        # ------------------------------------------------------------------
        # Task 4: Reverse Engineering Audit (Model String Decomposition)
        # ------------------------------------------------------------------
        task_4 = {
            "instruction": (
                "Deconstruct the Copeland model string into its functional mechanical, electrical, and refrigerant attributes."
            ),
            "input": f"Analyze nomenclature and characteristics for: {model}",
            "output": json.dumps({
                "model_identifier": model,
                "refrigerant_compatibility": refrig,
                "compression_technology": comp_type,
                "application_domain": application,
                "motor_voltage": voltage,
                "phase_count": phase,
                "electrical_frequency": freq,
                "displacement_in3_rev": disp_in3,
                "rated_rpm": speed_rpm
            }, indent=2)
        }
        dataset_records.append(task_4)

    # Deterministic split: 85% Train, 15% Validation
    random.seed(42)
    random.shuffle(dataset_records)

    split_index = int(len(dataset_records) * 0.85)
    train_set = dataset_records[:split_index]
    val_set = dataset_records[split_index:]

    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for item in train_set:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for item in val_set:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Extraction & generation complete:")
    print(f"  - Total Generated Samples: {len(dataset_records)}")
    print(f"  - Training Set:            {len(train_set)} -> {train_path}")
    print(f"  - Validation Set:          {len(val_set)} -> {val_path}")


if __name__ == "__main__":
    main()