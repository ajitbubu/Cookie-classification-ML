"""
Model Trainer for Cookie Classification

Trains Random Forest and other ML models on labeled cookie data.
Handles data preparation, training, evaluation, and model persistence.
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
import joblib
from datetime import datetime

from .config import (
    TRAINING_CSV,
    MODEL_FILE,
    SCALER_FILE,
    LABEL_ENCODER_FILE,
    METADATA_FILE,
    COOKIE_CATEGORIES,
    RANDOM_FOREST_PARAMS,
    TRAIN_TEST_SPLIT as TEST_SIZE,
    CROSS_VALIDATION_FOLDS,
    TARGET_ACCURACY,
    FEATURE_NAMES,
)
from .feature_extractor import FeatureExtractor


class ModelTrainer:
    """
    Train and evaluate ML models for cookie classification.

    Workflow:
    1. Load labeled training data
    2. Extract features using FeatureExtractor
    3. Split train/test sets
    4. Train Random Forest classifier
    5. Evaluate performance
    6. Save model artifacts
    """

    def __init__(self, training_data_path: Optional[Path] = None):
        """
        Initialize model trainer.

        Args:
            training_data_path: Path to labeled cookies CSV (defaults to config)
        """
        self.training_data_path = training_data_path or TRAINING_CSV
        self.feature_extractor = FeatureExtractor()
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = FEATURE_NAMES

    def load_training_data(self) -> pd.DataFrame:
        """
        Load labeled training data from CSV.

        Returns:
            DataFrame with labeled cookies
        """
        print(f"Loading training data from {self.training_data_path}...")

        if not self.training_data_path.exists():
            raise FileNotFoundError(
                f"Training data not found: {self.training_data_path}\n"
                f"Run: python scripts/bootstrap_training_data.py"
            )

        df = pd.read_csv(self.training_data_path)
        print(f"  ✓ Loaded {len(df)} labeled cookies")

        # Validate required columns
        required_columns = ["cookie_name", "domain", "category"]
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        return df

    def prepare_data(
        self, df: pd.DataFrame, test_size: float = TEST_SIZE
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare training and test datasets.

        Args:
            df: Labeled cookie DataFrame
            test_size: Fraction of data for testing

        Returns:
            (X_train, X_test, y_train, y_test)
        """
        print("\nPreparing features...")

        # Extract features for each cookie
        cookies_list = df.to_dict("records")
        features_df = self.feature_extractor.extract_batch(cookies_list)

        # Get labels
        labels = df["category"].values

        # Encode labels to numeric
        y = self.label_encoder.fit_transform(labels)

        print(f"  ✓ Extracted {len(features_df.columns)} features per cookie")
        print(f"  ✓ Categories: {list(self.label_encoder.classes_)}")

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            features_df, y, test_size=test_size, random_state=42, stratify=y
        )

        print(f"\nDataset split:")
        print(f"  Training samples: {len(X_train)}")
        print(f"  Testing samples:  {len(X_test)}")

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        return (
            pd.DataFrame(X_train_scaled, columns=features_df.columns),
            pd.DataFrame(X_test_scaled, columns=features_df.columns),
            y_train,
            y_test,
        )

    def train_random_forest(
        self, X_train: pd.DataFrame, y_train: pd.Series, params: Optional[Dict] = None
    ) -> RandomForestClassifier:
        """
        Train Random Forest classifier.

        Args:
            X_train: Training features
            y_train: Training labels
            params: Model hyperparameters (defaults to config)

        Returns:
            Trained RandomForestClassifier
        """
        print("\nTraining Random Forest...")

        params = params or RANDOM_FOREST_PARAMS
        print(f"  Hyperparameters: {params}")

        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)

        print("  ✓ Training complete")

        self.model = model
        return model

    def evaluate(
        self, X_test: pd.DataFrame, y_test: pd.Series
    ) -> Dict[str, Any]:
        """
        Evaluate model performance on test set.

        Args:
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary of evaluation metrics
        """
        print("\nEvaluating model...")

        if self.model is None:
            raise ValueError("Model not trained. Call train_random_forest() first.")

        # Predictions
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)

        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average="macro")
        f1_weighted = f1_score(y_test, y_pred, average="weighted")

        print(f"\n  Overall Accuracy: {accuracy:.3f}")
        print(f"  F1 Score (macro): {f1_macro:.3f}")
        print(f"  F1 Score (weighted): {f1_weighted:.3f}")

        # Classification report
        print("\n  Per-Class Performance:")
        report = classification_report(
            y_test,
            y_pred,
            target_names=self.label_encoder.classes_,
            output_dict=False,
        )
        print(report)

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print("\n  Confusion Matrix:")
        print(f"  {' '.join([f'{c:12s}' for c in self.label_encoder.classes_])}")
        for i, row in enumerate(cm):
            print(f"  {self.label_encoder.classes_[i]:12s} {row}")

        # Feature importance
        feature_importance = pd.DataFrame({
            "feature": X_test.columns,
            "importance": self.model.feature_importances_
        }).sort_values("importance", ascending=False)

        print("\n  Top 10 Most Important Features:")
        for idx, row in feature_importance.head(10).iterrows():
            print(f"    {row['feature']:30s}: {row['importance']:.4f}")

        # Check if meets target
        meets_target = accuracy >= TARGET_ACCURACY
        status = "✓ PASSED" if meets_target else "✗ FAILED"
        print(f"\n  Target Accuracy: {TARGET_ACCURACY:.2%} ... {status}")

        return {
            "accuracy": accuracy,
            "f1_macro": f1_macro,
            "f1_weighted": f1_weighted,
            "classification_report": classification_report(
                y_test, y_pred, target_names=self.label_encoder.classes_, output_dict=True
            ),
            "confusion_matrix": cm.tolist(),
            "feature_importance": feature_importance.to_dict("records"),
            "meets_target": meets_target,
        }

    def cross_validate(
        self, X_train: pd.DataFrame, y_train: pd.Series, cv_folds: int = CROSS_VALIDATION_FOLDS
    ) -> float:
        """
        Perform cross-validation to assess model robustness.

        Args:
            X_train: Training features
            y_train: Training labels
            cv_folds: Number of cross-validation folds

        Returns:
            Mean cross-validation score
        """
        print(f"\nPerforming {cv_folds}-fold cross-validation...")

        scores = cross_val_score(
            self.model, X_train, y_train, cv=cv_folds, scoring="accuracy"
        )

        print(f"  CV Scores: {scores}")
        print(f"  Mean: {scores.mean():.3f} (+/- {scores.std() * 2:.3f})")

        return scores.mean()

    def hyperparameter_tuning(
        self, X_train: pd.DataFrame, y_train: pd.Series
    ) -> Dict[str, Any]:
        """
        Perform grid search for optimal hyperparameters.

        Args:
            X_train: Training features
            y_train: Training labels

        Returns:
            Best parameters found
        """
        print("\nPerforming hyperparameter tuning...")

        param_grid = {
            "n_estimators": [50, 100, 200],
            "max_depth": [10, 15, 20, None],
            "min_samples_split": [5, 10, 20],
            "min_samples_leaf": [2, 5, 10],
            "max_features": ["sqrt", "log2"],
        }

        grid_search = GridSearchCV(
            RandomForestClassifier(random_state=42, n_jobs=-1),
            param_grid,
            cv=3,
            scoring="f1_macro",
            verbose=1,
            n_jobs=-1,
        )

        grid_search.fit(X_train, y_train)

        print(f"\n  Best parameters: {grid_search.best_params_}")
        print(f"  Best F1 score: {grid_search.best_score_:.3f}")

        self.model = grid_search.best_estimator_

        return grid_search.best_params_

    def save_model(self, metrics: Optional[Dict] = None) -> None:
        """
        Save trained model and artifacts to disk.

        Args:
            metrics: Evaluation metrics to include in metadata
        """
        print("\nSaving model artifacts...")

        if self.model is None:
            raise ValueError("No model to save. Train a model first.")

        # Create models directory if needed
        MODEL_FILE.parent.mkdir(exist_ok=True)

        # Save model
        joblib.dump(self.model, MODEL_FILE)
        print(f"  ✓ Model saved to {MODEL_FILE}")

        # Save scaler
        joblib.dump(self.scaler, SCALER_FILE)
        print(f"  ✓ Scaler saved to {SCALER_FILE}")

        # Save label encoder
        joblib.dump(self.label_encoder, LABEL_ENCODER_FILE)
        print(f"  ✓ Label encoder saved to {LABEL_ENCODER_FILE}")

        # Save metadata
        metadata = {
            "model_version": "1.0",
            "model_type": "RandomForestClassifier",
            "trained_date": datetime.now().isoformat(),
            "categories": list(self.label_encoder.classes_),
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "hyperparameters": self.model.get_params(),
        }

        if metrics:
            metadata["metrics"] = metrics

        with open(METADATA_FILE, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"  ✓ Metadata saved to {METADATA_FILE}")

    def load_model(self) -> None:
        """Load trained model and artifacts from disk."""
        print("Loading model artifacts...")

        if not MODEL_FILE.exists():
            raise FileNotFoundError(
                f"Model not found: {MODEL_FILE}\n"
                f"Train a model first with: python scripts/train_model.py"
            )

        self.model = joblib.load(MODEL_FILE)
        self.scaler = joblib.load(SCALER_FILE)
        self.label_encoder = joblib.load(LABEL_ENCODER_FILE)

        print(f"  ✓ Model loaded from {MODEL_FILE}")

        # Load metadata
        if METADATA_FILE.exists():
            with open(METADATA_FILE) as f:
                metadata = json.load(f)
            print(f"  ✓ Model version: {metadata['model_version']}")
            print(f"  ✓ Trained: {metadata['trained_date']}")


def main():
    """
    Main training script.

    Runs complete training pipeline:
    1. Load data
    2. Prepare features
    3. Train model
    4. Evaluate
    5. Save artifacts
    """
    print("=" * 60)
    print("COOKIE CLASSIFIER MODEL TRAINING")
    print("=" * 60)

    trainer = ModelTrainer()

    # Load and prepare data
    df = trainer.load_training_data()
    X_train, X_test, y_train, y_test = trainer.prepare_data(df)

    # Train model
    trainer.train_random_forest(X_train, y_train)

    # Cross-validation
    cv_score = trainer.cross_validate(X_train, y_train)

    # Evaluate
    metrics = trainer.evaluate(X_test, y_test)
    metrics["cv_accuracy"] = cv_score

    # Save model
    trainer.save_model(metrics)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Model saved to: {MODEL_FILE}")
    print(f"Accuracy: {metrics['accuracy']:.3f}")
    print(f"F1 Score: {metrics['f1_macro']:.3f}")
    print("\nNext step: Test the classifier with:")
    print("  python scripts/test_classifier.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
