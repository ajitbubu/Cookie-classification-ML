#!/usr/bin/env python3
"""
Training Script for Cookie Classifier

Trains Random Forest model on labeled cookie data and saves artifacts.

Usage:
    python scripts/train_model.py [--tune]

Options:
    --tune    Perform hyperparameter tuning (slower but better accuracy)
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ml_classifier.model_trainer import ModelTrainer


def main():
    """Main training workflow."""
    import argparse

    parser = argparse.ArgumentParser(description="Train cookie classifier model")
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Perform hyperparameter tuning (takes longer)",
    )
    parser.add_argument(
        "--data",
        type=str,
        help="Path to training data CSV (defaults to training_data/labeled_cookies.csv)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("COOKIE CLASSIFIER MODEL TRAINING")
    print("=" * 60)

    # Initialize trainer
    if args.data:
        trainer = ModelTrainer(training_data_path=Path(args.data))
    else:
        trainer = ModelTrainer()

    # Load and prepare data
    df = trainer.load_training_data()

    # Check minimum samples
    if len(df) < 50:
        print("\n⚠ WARNING: Training data has < 50 samples!")
        print("  For better accuracy, add more labeled cookies.")
        print("  Consider running: python scripts/bootstrap_training_data.py")
        print()

    X_train, X_test, y_train, y_test = trainer.prepare_data(df)

    # Hyperparameter tuning if requested
    if args.tune:
        print("\n" + "=" * 60)
        print("HYPERPARAMETER TUNING (this may take several minutes)")
        print("=" * 60)
        best_params = trainer.hyperparameter_tuning(X_train, y_train)
        print(f"\nBest parameters found: {best_params}")
    else:
        # Train with default parameters
        trainer.train_random_forest(X_train, y_train)

    # Cross-validation
    cv_score = trainer.cross_validate(X_train, y_train)

    # Evaluate on test set
    metrics = trainer.evaluate(X_test, y_test)
    metrics["cv_accuracy"] = cv_score

    # Save model
    trainer.save_model(metrics)

    # Final summary
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"✓ Model saved successfully")
    print(f"✓ Test Accuracy: {metrics['accuracy']:.3f}")
    print(f"✓ F1 Score (macro): {metrics['f1_macro']:.3f}")
    print(f"✓ Cross-Validation Accuracy: {cv_score:.3f}")

    if metrics["meets_target"]:
        print(f"✓ Model meets target accuracy!")
    else:
        print(f"⚠ Model accuracy below target. Consider:")
        print(f"  - Adding more training data")
        print(f"  - Running with --tune flag")
        print(f"  - Checking data quality")

    print("\nNext steps:")
    print("  1. Test classifier: python scripts/test_classifier.py")
    print("  2. View demo: python ml_classifier/classifier.py")
    print("  3. Integrate into cookie_scanner.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
