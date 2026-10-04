import os
import yaml
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

def main():
    config_path = "projects/02-spec-adapter/configs/qlora_config.yaml"
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # 1. Quantization Configuration (NF4 + Double Quantization)
    compute_dtype = getattr(torch, cfg["bnb_config"]["bnb_4bit_compute_dtype"])
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=cfg["bnb_config"]["load_in_4bit"],
        bnb_4bit_quant_type=cfg["bnb_config"]["bnb_4bit_quant_type"],
        bnb_4bit_use_double_quant=cfg["bnb_config"]["bnb_4bit_use_double_quant"],
        bnb_4bit_compute_dtype=compute_dtype
    )

    # 2. Tokenizer Setup
    tokenizer = AutoTokenizer.from_pretrained(cfg["model_id"], trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # 3. Base Model with 4-bit NormalFloat Loading
    print(f"Loading base model {cfg['model_id']} in 4-bit NF4...")
    model = AutoModelForCausalLM.from_pretrained(
        cfg["model_id"],
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    model = prepare_model_for_kbit_training(model)

    # 4. LoRA Adapter Injection
    peft_config = LoraConfig(
        r=cfg["peft_config"]["r"],
        lora_alpha=cfg["peft_config"]["lora_alpha"],
        lora_dropout=cfg["peft_config"]["lora_dropout"],
        bias=cfg["peft_config"]["bias"],
        task_type=cfg["peft_config"]["task_type"],
        target_modules=cfg["peft_config"]["target_modules"]
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 5. Load Processed Datasets
    data_files = {
        "train": "projects/02-spec-adapter/data/processed/train.jsonl",
        "validation": "projects/02-spec-adapter/data/processed/val.jsonl"
    }
    raw_datasets = load_dataset("json", data_files=data_files)

    def format_chatml(sample):
        text = (
            f"<|im_start|>system\n"
            f"You are a specialized mechanical specification and electrical sizing assistant. "
            f"Respond strictly in valid JSON.<|im_end|>\n"
            f"<|im_start|>user\n"
            f"{sample['instruction']}\n{sample['input']}<|im_end|>\n"
            f"<|im_start|>assistant\n"
            f"{sample['output']}<|im_end|>"
        )
        return {"text": text}

    train_data = raw_datasets["train"].map(format_chatml)
    val_data = raw_datasets["validation"].map(format_chatml)

    # 6. SFT Training Arguments
    t_args = cfg["training_args"]
    training_args = TrainingArguments(
        output_dir=t_args["output_dir"],
        per_device_train_batch_size=t_args["per_device_train_batch_size"],
        gradient_accumulation_steps=t_args["gradient_accumulation_steps"],
        learning_rate=t_args["learning_rate"],
        lr_scheduler_type=t_args["lr_scheduler_type"],
        warmup_ratio=t_args["warmup_ratio"],
        num_train_epochs=t_args["num_train_epochs"],
        logging_steps=t_args["logging_steps"],
        eval_strategy=t_args["eval_strategy"],
        eval_steps=t_args["eval_steps"],
        save_strategy=t_args["save_strategy"],
        save_steps=t_args["save_steps"],
        save_total_limit=t_args["save_total_limit"],
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        fp16=not (torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
        report_to="none"
    )

    # 7. Trainer Execution
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_data,
        eval_dataset=val_data,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=t_args["max_seq_length"],
        tokenizer=tokenizer,
        args=training_args
    )

    print("Beginning QLoRA training run...")
    trainer.train()

    # 8. Save Final Trained LoRA Adapter
    final_adapter_path = "./output/spec_adapter_final"
    trainer.model.save_pretrained(final_adapter_path)
    tokenizer.save_pretrained(final_adapter_path)
    print(f"Adapter saved successfully to: {final_adapter_path}")

if __name__ == "__main__":
    main()