"""Service to train a classifier on generated training data."""
from typing import Dict, Any, List, Optional, Tuple
import os
import json
import pickle
from datetime import datetime


# Lazy imports to avoid loading heavy ML libraries on every request
_transformers_loaded = False
_torch_loaded = False


def _load_ml_libraries():
    """Lazy load ML libraries."""
    global _transformers_loaded, _torch_loaded
    
    if not _transformers_loaded:
        global AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
        global torch, Dataset
        
        from transformers import (
            AutoTokenizer, 
            AutoModelForSequenceClassification,
            Trainer,
            TrainingArguments
        )
        import torch
        from torch.utils.data import Dataset
        
        _transformers_loaded = True
        _torch_loaded = True


class TextClassificationDataset:
    """PyTorch dataset for text classification."""
    
    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': label
        }


def train_classifier(
    dataset: Dict[str, Any],
    model_output_dir: str,
    model_name: str = "distilbert-base-uncased",
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5
) -> Dict[str, Any]:
    """
    Train a DistilBERT classifier on the generated dataset.
    
    Args:
        dataset: Training dataset with 'train' and 'test' splits
        model_output_dir: Directory to save the trained model
        model_name: HuggingFace model to use
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate
        
    Returns:
        Dict with training metrics and model path
    """
    _load_ml_libraries()
    
    print(f"DEBUG: Training classifier on {len(dataset['train'])} examples")
    print(f"DEBUG: Using model: {model_name}")
    
    os.makedirs(model_output_dir, exist_ok=True)
    
    # Prepare data
    train_texts = [f"User: {ex['user']}\nAssistant: {ex['assistant']}" for ex in dataset['train']]
    train_labels = [ex['label'] for ex in dataset['train']]
    
    test_texts = [f"User: {ex['user']}\nAssistant: {ex['assistant']}" for ex in dataset['test']]
    test_labels = [ex['label'] for ex in dataset['test']]
    
    print(f"DEBUG: Train size: {len(train_texts)}, Test size: {len(test_texts)}")
    
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2
    )
    
    # Create datasets
    train_dataset = TextClassificationDataset(train_texts, train_labels, tokenizer)
    test_dataset = TextClassificationDataset(test_texts, test_labels, tokenizer)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=model_output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        warmup_steps=100,
        weight_decay=0.01,
        logging_dir=os.path.join(model_output_dir, 'logs'),
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        learning_rate=learning_rate,
    )
    
    # Define compute metrics
    def compute_metrics(eval_pred):
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support
        
        logits, labels = eval_pred
        predictions = logits.argmax(axis=-1)
        
        accuracy = accuracy_score(labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average='binary'
        )
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }
    
    # Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        compute_metrics=compute_metrics,
    )
    
    print("DEBUG: Starting training...")
    train_result = trainer.train()
    
    # Evaluate
    print("DEBUG: Evaluating model...")
    eval_result = trainer.evaluate()
    
    # Save model
    trainer.save_model(model_output_dir)
    tokenizer.save_pretrained(model_output_dir)
    
    # Save training info
    training_info = {
        "issue_description": dataset.get("issue_description", ""),
        "issue_hash": dataset.get("issue_hash", ""),
        "model_name": model_name,
        "train_size": len(train_texts),
        "test_size": len(test_texts),
        "epochs": epochs,
        "metrics": eval_result,
        "trained_at": datetime.now().isoformat()
    }
    
    with open(os.path.join(model_output_dir, "training_info.json"), 'w') as f:
        json.dump(training_info, f, indent=2)
    
    print(f"DEBUG: Training complete. Metrics: {eval_result}")
    
    return {
        "model_path": model_output_dir,
        "metrics": eval_result,
        "training_info": training_info
    }


def load_classifier(model_dir: str) -> Tuple[Any, Any]:
    """
    Load a trained classifier from disk.
    
    Args:
        model_dir: Directory containing the saved model
        
    Returns:
        Tuple of (model, tokenizer)
    """
    _load_ml_libraries()
    
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    
    return model, tokenizer


def predict_single(model, tokenizer, text: str) -> Dict[str, Any]:
    """
    Make a prediction on a single text.
    
    Args:
        model: The trained model
        tokenizer: The tokenizer
        text: Text to classify
        
    Returns:
        Dict with prediction and confidence
    """
    _load_ml_libraries()
    
    inputs = tokenizer(
        text,
        truncation=True,
        padding='max_length',
        max_length=512,
        return_tensors='pt'
    )
    
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        predicted_class = probs.argmax().item()
        confidence = probs.max().item()
    
    return {
        "prediction": "MATCH" if predicted_class == 1 else "NO_MATCH",
        "confidence": confidence,
        "probabilities": {
            "NO_MATCH": probs[0][0].item(),
            "MATCH": probs[0][1].item()
        }
    }


def predict_batch(model, tokenizer, texts: List[str], batch_size: int = 32) -> List[Dict[str, Any]]:
    """
    Make predictions on a batch of texts.
    
    Args:
        model: The trained model
        tokenizer: The tokenizer
        texts: List of texts to classify
        batch_size: Batch size for inference
        
    Returns:
        List of prediction dicts
    """
    _load_ml_libraries()
    
    results = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        
        inputs = tokenizer(
            batch_texts,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors='pt'
        )
        
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            predicted_classes = probs.argmax(dim=-1)
            confidences = probs.max(dim=-1).values
        
        for j, (pred, conf, prob) in enumerate(zip(predicted_classes, confidences, probs)):
            results.append({
                "prediction": "MATCH" if pred.item() == 1 else "NO_MATCH",
                "confidence": conf.item(),
                "probabilities": {
                    "NO_MATCH": prob[0].item(),
                    "MATCH": prob[1].item()
                }
            })
    
    return results

