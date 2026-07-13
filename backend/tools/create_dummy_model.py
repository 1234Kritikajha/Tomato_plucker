#!/usr/bin/env python3
"""
Create a dummy Keras model for testing purposes.
This ensures the model loading system works even without a trained model.
"""

import numpy as np
from pathlib import Path
import json

def create_dummy_model():
    """Create a simple dummy model for testing."""
    try:
        import tensorflow as tf
        from tensorflow import keras
        
        # Create a simple multi-output model
        input_layer = keras.Input(shape=(224, 224, 3), name='image_input')
        
        # Simple feature extraction
        x = keras.layers.Conv2D(32, 3, activation='relu')(input_layer)
        x = keras.layers.MaxPooling2D()(x)
        x = keras.layers.Conv2D(64, 3, activation='relu')(x)
        x = keras.layers.MaxPooling2D()(x)
        x = keras.layers.GlobalAveragePooling2D()(x)
        x = keras.layers.Dense(128, activation='relu')(x)
        
        # Ripeness output (3 classes: Ripe, Unripe, Half-Ripe)
        ripeness_output = keras.layers.Dense(3, activation='softmax', name='ripeness')(x)
        
        # Condition output (2 classes: Healthy, Damaged)
        condition_output = keras.layers.Dense(2, activation='softmax', name='condition')(x)
        
        model = keras.Model(inputs=input_layer, outputs=[ripeness_output, condition_output])
        
        # Compile the model
        model.compile(
            optimizer='adam',
            loss={
                'ripeness': 'categorical_crossentropy',
                'condition': 'categorical_crossentropy'
            },
            metrics={
                'ripeness': ['accuracy'],
                'condition': ['accuracy']
            }
        )
        
        return model
    except ImportError:
        print("TensorFlow not available, skipping dummy model creation")
        return None

def main():
    """Main function to create dummy model and config."""
    models_dir = Path(__file__).resolve().parent.parent / "storage" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Create dummy model
    print("Creating dummy model...")
    model = create_dummy_model()
    
    if model is not None:
        model_path = models_dir / "tomato_plucking_model.keras"
        model.save(model_path)
        print(f"Dummy model saved to {model_path}")
        
        # Also create a backup copy
        backup_path = models_dir / "checkpoints" / "dummy_v1.keras"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(backup_path)
        print(f"Backup model saved to {backup_path}")
    else:
        print("Skipping model creation (TensorFlow not available)")
    
    # Create model config
    model_config = {
        "input_size": [224, 224, 3],
        "ripeness_classes": ["Ripe", "Unripe", "Half-Ripe"],
        "condition_classes": ["Healthy", "Damaged"],
        "model_type": "multi_output",
        "framework": "tensorflow",
        "version": "1.0.0"
    }
    
    config_path = models_dir / "model_config.json"
    with open(config_path, 'w') as f:
        json.dump(model_config, f, indent=2)
    
    print(f"Model config saved to {config_path}")
    
    # Create class names file
    class_names = {
        "ripeness": ["Ripe", "Unripe", "Half-Ripe"],
        "condition": ["Healthy", "Damaged"]
    }
    
    class_names_path = models_dir / "class_names.json"
    with open(class_names_path, 'w') as f:
        json.dump(class_names, f, indent=2)
    
    print(f"Class names saved to {class_names_path}")
    print("Done!")

if __name__ == "__main__":
    main()