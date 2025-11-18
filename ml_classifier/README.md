## ML Cookie Classifier

AI-powered cookie classification using machine learning (no external LLM APIs).

### Overview

Automatically categorizes cookies into:
- **Necessary**: Essential for website functionality
- **Functional**: User preferences and features
- **Analytics**: Performance tracking and analytics
- **Advertising**: Marketing and ad tracking

### Features

✅ **Zero External Dependencies**: No OpenAI, Anthropic, or other LLM APIs
✅ **Fast Inference**: <1ms per cookie classification
✅ **Confidence Scoring**: Every prediction includes confidence (0-100%)
✅ **Evidence Generation**: Explains WHY each cookie was classified
✅ **Hybrid Strategy**: Falls back to rules for low-confidence predictions
✅ **Batch Processing**: Efficient classification of hundreds of cookies
✅ **Active Learning**: Continuous improvement with admin feedback

### Architecture

```
┌─────────────────────────────────────────────┐
│         Cookie Input (name, domain, etc.)    │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  FeatureExtractor (30+ features)             │
│  • Name patterns (entropy, prefixes)         │
│  • Domain analysis (party, reputation)       │
│  • Duration categorization                   │
│  • Security flags (httpOnly, secure)         │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  Random Forest Classifier                    │
│  • 100 decision trees                        │
│  • Balanced class weights                    │
│  • Probability distributions                 │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  Classification Result                       │
│  • Category prediction                       │
│  • Confidence score (0.0-1.0)                │
│  • Evidence explanation                      │
│  • Fallback recommendation                   │
└─────────────────────────────────────────────┘
```

### Quick Start

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Key ML packages:
- `scikit-learn`: Random Forest classifier
- `pandas`: Data processing
- `numpy`: Numerical operations
- `joblib`: Model serialization
- `shap`: Model explainability

#### 2. Generate Training Data

```bash
python scripts/bootstrap_training_data.py
```

This creates `training_data/labeled_cookies.csv` with ~100 labeled cookies extracted from:
- `cookie_rules.json` patterns
- Known cookie datasets (Google, Facebook, Hotjar, etc.)
- Synthetic variations

**Note**: For production accuracy (>90%), you'll need 10,000+ labeled samples. The bootstrap provides a starting point.

#### 3. Train the Model

```bash
# Basic training (fast)
python scripts/train_model.py

# With hyperparameter tuning (slower, better accuracy)
python scripts/train_model.py --tune
```

Output:
- `models/cookie_classifier_v1.pkl` - Trained Random Forest model
- `models/feature_scaler.pkl` - Feature scaler
- `models/label_encoder.pkl` - Category label encoder
- `models/metadata.json` - Model version and metrics

#### 4. Test the Classifier

```bash
# Batch test with predefined cookies
python scripts/test_classifier.py

# Interactive mode
python scripts/test_classifier.py --interactive
```

### Usage Examples

#### Basic Classification

```python
from ml_classifier import MLCookieClassifier

# Initialize classifier
classifier = MLCookieClassifier()

# Classify a cookie
cookie = {
    "name": "_ga",
    "domain": ".google-analytics.com",
    "cookie_duration": "730 days",
    "cookie_type": "Third Party",
    "httpOnly": False,
    "secure": True,
    "sameSite": "None",
}

result = classifier.classify(cookie)

print(f"Category: {result.category}")
print(f"Confidence: {result.confidence:.1%}")
print(f"Evidence: {result.evidence}")
```

Output:
```
Category: Analytics
Confidence: 94.2%
Evidence:
  - Domain '.google-analytics.com' is recognized analytics vendor
  - Cookie name '_ga' matches known analytics pattern
  - Duration '730 days' typical for analytics cookies
  - High confidence prediction (94.2%)
```

#### Batch Classification

```python
cookies = [
    {"name": "_ga", "domain": ".google-analytics.com", ...},
    {"name": "sessionid", "domain": ".example.com", ...},
    {"name": "_fbp", "domain": ".facebook.com", ...},
]

results = classifier.classify_batch(cookies)

for cookie, result in zip(cookies, results):
    print(f"{cookie['name']}: {result.category} ({result.confidence:.1%})")
```

#### Hybrid Strategy (ML + Rules)

```python
def classify_cookie_hybrid(cookie):
    # 1. Check database override (highest priority)
    if db_result := get_db_classification(cookie):
        return db_result

    # 2. Try ML classifier
    ml_result = classifier.classify(cookie)

    if ml_result.confidence >= 0.75:  # High confidence
        return ml_result

    # 3. Fallback to IAB GVL
    if iab_result := get_iab_classification(cookie):
        return iab_result

    # 4. Fallback to rules
    if rules_result := get_rules_classification(cookie):
        # Blend ML + rules if ML confidence is medium
        if 0.4 <= ml_result.confidence < 0.75:
            return blend_predictions(ml_result, rules_result)
        return rules_result

    # 5. Return ML prediction with low confidence flag
    ml_result.requires_review = True
    return ml_result
```

### Model Training Details

#### Feature Engineering (30+ Features)

**Name-based (8 features):**
- `name_length`: Character count
- `has_underscore`: Contains "_"
- `has_numbers`: Contains digits
- `name_entropy`: Randomness score (0-1)
- `name_prefix_encoded`: First 3 chars (encoded)
- `vendor_fingerprint`: Detected vendor (Google, Facebook, etc.)

**Domain-based (7 features):**
- `is_third_party`: First vs third party
- `domain_levels`: Subdomain count
- `tld_encoded`: Top-level domain
- `is_known_analytics`: Known analytics domain
- `is_known_advertising`: Known ad domain
- `domain_entropy`: Domain randomness

**Duration-based (3 features):**
- `is_session`: Session cookie (0 duration)
- `duration_days`: Duration in days
- `duration_category_encoded`: Session/Short/Medium/Long

**Security (4 features):**
- `httpOnly`: HttpOnly flag
- `secure`: Secure flag
- `sameSite_encoded`: Strict=2, Lax=1, None=0
- `security_score`: Composite metric

**Behavioral (4 features):**
- `size`: Cookie size in bytes
- `set_after_accept`: Set after consent
- `path_is_root`: Path is "/"

**Pattern Matching (4 features):**
- `matches_analytics_pattern`: Matches known analytics name
- `matches_advertising_pattern`: Matches ad pattern
- `matches_necessary_pattern`: Matches necessary pattern
- `matches_functional_pattern`: Matches functional pattern

#### Training Parameters

```python
RANDOM_FOREST_PARAMS = {
    "n_estimators": 100,       # 100 decision trees
    "max_depth": 15,           # Max tree depth
    "min_samples_split": 10,   # Min samples to split
    "min_samples_leaf": 5,     # Min samples per leaf
    "max_features": "sqrt",    # Features per split
    "class_weight": "balanced", # Handle imbalanced classes
    "random_state": 42,
    "n_jobs": -1,              # Use all CPU cores
}
```

#### Performance Targets

- **Overall Accuracy**: ≥85% (baseline), ≥90% (production)
- **Per-Class F1-Score**: ≥0.80
- **Necessary Precision**: ≥0.95 (critical for compliance)
- **Advertising Recall**: ≥0.90 (important for privacy)
- **Inference Time**: <1ms per cookie

### Confidence Levels

```python
HIGH_CONFIDENCE_THRESHOLD = 0.75   # Use ML prediction directly
MEDIUM_CONFIDENCE_THRESHOLD = 0.50  # Blend with rules
LOW_CONFIDENCE_THRESHOLD = 0.40     # Flag for manual review
```

**Classification Strategy:**
- **≥75% confidence**: Trust ML prediction
- **50-75% confidence**: Blend ML with rule-based fallback
- **<50% confidence**: Use fallback, flag for admin review

### Continuous Improvement

#### Active Learning Workflow

1. **Identify low-confidence predictions** (confidence < 60%)
2. **Admin reviews and corrects** via annotation tool
3. **Add corrections to training data**
4. **Retrain model weekly** with updated dataset
5. **A/B test new model** before deployment

```bash
# Retrain with updated data
python scripts/train_model.py --data training_data/labeled_cookies_updated.csv

# Compare model versions
# (Feature coming in Phase 5)
```

### File Structure

```
ml_classifier/
├── __init__.py              # Module exports
├── config.py                # Configuration settings
├── feature_extractor.py     # Feature engineering
├── model_trainer.py         # Training pipeline
├── classifier.py            # Inference engine
└── README.md               # This file

models/                      # Trained model artifacts
├── cookie_classifier_v1.pkl
├── feature_scaler.pkl
├── label_encoder.pkl
└── metadata.json

training_data/               # Training datasets
├── labeled_cookies.csv      # Bootstrap dataset
├── validation_cookies.csv   # (Future)
└── test_cookies.csv        # (Future)

scripts/                     # Utility scripts
├── bootstrap_training_data.py
├── train_model.py
└── test_classifier.py
```

### Integration with Cookie Scanner

Modify `cookie_scanner.py` to use ML classifier:

```python
from ml_classifier import MLCookieClassifier

# Initialize once at module level
ml_classifier = MLCookieClassifier()

def classify_cookie(cookie):
    """Classify cookie using hybrid ML + rules approach."""
    # Try ML first
    ml_result = ml_classifier.classify(cookie)

    # Add ML fields to cookie object
    cookie["ml_confidence"] = ml_result.confidence
    cookie["ml_probabilities"] = ml_result.probabilities
    cookie["classification_source"] = ml_result.source
    cookie["classification_evidence"] = ml_result.evidence

    # Use hybrid strategy
    if ml_result.confidence >= 0.75:
        cookie["category"] = ml_result.category
        cookie["classification_source"] = "ML_High"
    else:
        # Fallback to existing rules
        cookie["category"] = get_rules_based_category(cookie)
        cookie["classification_source"] = "Rules_Fallback"

        # Flag for review if very low confidence
        if ml_result.confidence < 0.5:
            cookie["requires_review"] = True

    return cookie
```

### API Endpoints for ML Admin

Add to `api/routers/ml_admin.py`:

```python
@router.get("/ml/metrics")
async def get_ml_metrics():
    """Get ML model performance metrics."""
    return {
        "model_version": "1.0",
        "accuracy": 0.87,
        "avg_confidence": 0.82,
        "predictions_count": 15234,
        "low_confidence_count": 423,
    }

@router.get("/ml/low-confidence")
async def get_low_confidence_cookies(limit: int = 100):
    """Get cookies needing manual review."""
    # Return cookies with confidence < 0.6
    pass

@router.post("/ml/feedback")
async def submit_feedback(cookie_id: str, correct_category: str):
    """Submit correction for retraining."""
    # Store in training_data/corrections.csv
    pass
```

### Troubleshooting

#### Issue: Model accuracy too low (<80%)

**Solutions:**
1. Add more training data (target: 10,000+ samples)
2. Run hyperparameter tuning: `python scripts/train_model.py --tune`
3. Check data quality and balance across categories
4. Use ensemble methods (combine multiple models)

#### Issue: Training data insufficient

**Solutions:**
1. Scrape public datasets (CookiePedia, IAB GVL)
2. Extract cookies from real scans
3. Use admin annotation tool for labeling
4. Generate more synthetic variations

#### Issue: Model not found error

```
FileNotFoundError: Model not found: models/cookie_classifier_v1.pkl
```

**Solution:**
```bash
python scripts/train_model.py
```

#### Issue: Low confidence on known cookies

**Solutions:**
1. Check if cookie patterns are in training data
2. Add specific examples to `KNOWN_COOKIES` in bootstrap script
3. Verify feature extraction is working correctly
4. Retrain with more diverse samples

### Future Enhancements

- [ ] **Ensemble Models**: Combine Random Forest + XGBoost + Logistic Regression
- [ ] **Deep Learning**: BERT-based model for cookie name embeddings
- [ ] **Transfer Learning**: Pre-trained privacy models
- [ ] **Online Learning**: Real-time model updates
- [ ] **Multi-lingual Support**: Non-English cookie names
- [ ] **Network Features**: Vendor co-occurrence patterns
- [ ] **ONNX Export**: Cross-platform model deployment
- [ ] **Model Monitoring Dashboard**: Drift detection, A/B testing

### References

- [IAB Global Vendor List](https://iabeurope.eu/vendor-list-tcf/)
- [CookiePedia](https://cookiepedia.co.uk/)
- [GDPR Cookie Categories](https://gdpr.eu/cookies/)
- [Scikit-learn Documentation](https://scikit-learn.org/)

---

**Version**: 1.0.0
**Last Updated**: 2025-11-18
**Status**: Phase 1 Complete (Foundation)
