# ML-Based Cookie Classifier Implementation Plan

## Overview
Implement an ML-powered cookie classification system that automatically categorizes cookies into **Strictly Necessary**, **Functionality**, **Analytics**, and **Advertising** categories using machine learning models trained on cookie features. Zero reliance on external LLM APIs.

---

## Current State Analysis

### Existing Cookie Classification System
- **Three-tier hierarchy**: Database → IAB GVL → Rules JSON
- **Rule-based matching**: Regex patterns in `cookie_rules.json`
- **Categories**: Necessary, Functional, Analytics, Advertising, Marketing, Targeting, Unknown
- **Limitations**:
  - Requires manual rule creation
  - Cannot handle new/unknown cookies intelligently
  - No confidence scoring
  - Binary match/no-match logic

### Available Cookie Features
From `cookie_scanner.py` and `models/scan.py`:
```python
{
    "name": str,              # Cookie name (e.g., "_ga", "sessionid")
    "domain": str,            # Domain (e.g., ".google.com")
    "path": str,              # Path (e.g., "/", "/api")
    "cookie_duration": str,   # Duration (e.g., "Session", "365 days")
    "size": int,              # Cookie size in bytes
    "httpOnly": bool,         # Security flag
    "secure": bool,           # Security flag
    "sameSite": str,          # "Strict", "Lax", "None"
    "cookie_type": str,       # "First Party" or "Third Party"
    "set_after_accept": bool  # Consent timing
}
```

---

## Technical Approach

### ML Model Selection
**Primary Model: Random Forest Classifier**
- Handles mixed feature types (categorical + numerical)
- Provides feature importance scores
- Outputs probability distributions (confidence)
- No external API dependencies
- Fast inference (<1ms per cookie)
- Interpretable (decision tree visualization)

**Alternative Models for Experimentation:**
1. **Gradient Boosting (XGBoost/LightGBM)**: Higher accuracy, slower training
2. **Logistic Regression**: Fast, interpretable baseline
3. **Neural Network (TensorFlow/PyTorch)**: For future deep learning experiments

**Tech Stack:**
- `scikit-learn`: Core ML framework
- `pandas`: Data processing
- `numpy`: Numerical operations
- `joblib`: Model serialization
- `ONNX Runtime` (optional): Cross-platform model deployment

---

## Architecture Design

### Component Structure

```
ml_classifier/
├── __init__.py
├── feature_extractor.py      # Extract ML features from cookie objects
├── model_trainer.py           # Training pipeline
├── classifier.py              # Inference engine
├── confidence_scorer.py       # Confidence & evidence generation
├── fallback_strategy.py       # Hybrid ML + rules approach
├── model_registry.py          # Model versioning & A/B testing
├── explainability.py          # SHAP/LIME for interpretability
└── monitoring.py              # Model performance tracking

models/                         # Trained model artifacts
├── cookie_classifier_v1.pkl
├── feature_scaler.pkl
├── label_encoder.pkl
└── metadata.json              # Model version, accuracy, features

training_data/
├── labeled_cookies.csv        # Training dataset
├── validation_cookies.csv     # Validation dataset
└── annotation_tool.py         # Admin labeling interface

analytics/
├── ml_metrics_calculator.py   # ML-specific metrics
└── model_drift_detector.py    # Data drift monitoring
```

---

## Feature Engineering

### Feature Extraction Pipeline

#### 1. **Name-Based Features** (40% importance)
```python
# Extract from cookie name
- name_length: int                    # Character count
- has_underscore: bool                # Contains "_"
- has_numbers: bool                   # Contains digits
- name_prefix: str                    # First 3 chars (e.g., "_ga", "sid")
- name_suffix: str                    # Last 3 chars
- vendor_fingerprint: str             # Extracted vendor hint (ga→Google, fbp→Facebook)
- name_entropy: float                 # Randomness score (0-1)
- known_pattern_match: str            # Closest known pattern
```

#### 2. **Domain-Based Features** (25% importance)
```python
# Extract from domain
- is_third_party: bool                # First vs third party
- domain_levels: int                  # Subdomain count
- tld: str                            # Top-level domain (.com, .co.uk)
- is_cdn: bool                        # CDN domain detection
- domain_reputation: str              # From vendor database (google, facebook, etc.)
- domain_entropy: float               # Randomness score
```

#### 3. **Duration-Based Features** (20% importance)
```python
# Extract from cookie_duration
- is_session: bool                    # Session cookie
- duration_days: float                # Converted to days
- duration_category: str              # "session", "short" (<30d), "medium" (30-365d), "long" (>365d)
- duration_score: float               # Normalized 0-1
```

#### 4. **Security Features** (10% importance)
```python
- httpOnly: bool
- secure: bool
- sameSite_encoded: int               # Strict=2, Lax=1, None=0
- security_score: float               # Composite security metric
```

#### 5. **Behavioral Features** (5% importance)
```python
- size: int                           # Cookie size
- set_after_accept: bool              # Consent timing
- path_is_root: bool                  # Path == "/"
```

**Total Features: ~30-35 features per cookie**

---

## Training Data Strategy

### Data Collection Approach

#### Phase 1: Bootstrap Dataset (Week 1-2)
1. **Leverage existing rules** (`cookie_rules.json`)
   - Extract ~500-1000 known cookies
   - Auto-label based on current categorization
   - Confidence: High for well-known cookies

2. **Scrape public datasets**
   - CookiePedia API (https://cookiepedia.co.uk)
   - IAB GVL vendor mappings
   - Privacy policy cookie lists
   - Target: 5,000-10,000 labeled cookies

3. **Generate synthetic variations**
   - Permutations of known cookie patterns
   - Augment training data to 15,000+ samples

#### Phase 2: Active Learning (Week 3-4)
1. **Admin annotation tool**
   - Web UI for quick labeling
   - Show top 100 low-confidence predictions daily
   - Bulk import from scan results
   - Export to training dataset

2. **Confidence-based sampling**
   - Select cookies with 40-60% confidence
   - Prioritize unknown domains
   - Focus on high-traffic cookies

#### Phase 3: Continuous Learning (Ongoing)
1. **Feedback loop**
   - Admin corrections stored
   - Weekly model retraining
   - A/B testing new versions

### Dataset Structure
```csv
cookie_name,domain,path,duration_days,is_session,httpOnly,secure,sameSite,cookie_type,size,set_after_accept,category,confidence,source
_ga,.google-analytics.com,/,730,False,False,True,None,Third Party,50,False,Analytics,1.0,IAB_GVL
sessionid,.example.com,/,0,True,True,True,Strict,First Party,32,False,Necessary,1.0,Manual
_fbp,.facebook.com,/,90,False,False,True,None,Third Party,42,True,Advertising,1.0,CookiePedia
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
**Goal**: Set up ML infrastructure and data pipeline

1. **Create ML module structure**
   ```bash
   mkdir ml_classifier training_data models
   touch ml_classifier/{__init__,feature_extractor,classifier,model_trainer}.py
   ```

2. **Install dependencies**
   ```bash
   pip install scikit-learn pandas numpy joblib shap matplotlib seaborn
   ```

3. **Extract training data from existing rules**
   - Script: `scripts/bootstrap_training_data.py`
   - Parse `cookie_rules.json` → labeled CSV
   - Fetch IAB GVL → labeled CSV
   - Merge and deduplicate

4. **Implement FeatureExtractor**
   - Input: Cookie model object
   - Output: Feature vector (pandas DataFrame row)
   - Unit tests for each feature

**Deliverables:**
- ✅ ML project structure
- ✅ 1,000+ labeled cookies from rules
- ✅ FeatureExtractor class with tests

---

### Phase 2: Model Training (Week 2)
**Goal**: Train initial classifier with baseline accuracy

1. **Implement ModelTrainer class**
   ```python
   class ModelTrainer:
       def prepare_data(self, csv_path)
       def train_random_forest(self, params)
       def evaluate(self, test_data)
       def save_model(self, model_path)
       def cross_validate(self, folds=5)
   ```

2. **Train baseline Random Forest**
   - Train/test split: 80/20
   - Hyperparameters:
     ```python
     {
         'n_estimators': 100,
         'max_depth': 15,
         'min_samples_split': 10,
         'class_weight': 'balanced'  # Handle imbalanced categories
     }
     ```
   - Target metrics:
     - Overall accuracy: >85%
     - Per-class F1-score: >0.80
     - Inference time: <1ms

3. **Hyperparameter tuning**
   - Grid search on validation set
   - Optimize for F1-score (handles imbalanced data)

4. **Model serialization**
   - Save model, scaler, encoders with `joblib`
   - Version metadata (accuracy, date, features)

**Deliverables:**
- ✅ Trained Random Forest model (v1.0)
- ✅ Evaluation report (confusion matrix, feature importance)
- ✅ Model artifacts in `models/` directory

---

### Phase 3: Integration (Week 3)
**Goal**: Integrate ML classifier into existing codebase

1. **Create MLCookieClassifier service**
   ```python
   # ml_classifier/classifier.py
   class MLCookieClassifier:
       def __init__(self, model_path):
           self.model = joblib.load(model_path)
           self.feature_extractor = FeatureExtractor()

       def classify(self, cookie: Cookie) -> ClassificationResult:
           # Extract features
           features = self.feature_extractor.extract(cookie)

           # Predict with probabilities
           probabilities = self.model.predict_proba(features)
           predicted_class = self.model.predict(features)[0]
           confidence = probabilities.max()

           return ClassificationResult(
               category=predicted_class,
               confidence=confidence,
               probabilities=dict(zip(self.model.classes_, probabilities[0])),
               source="ML_Model_v1.0"
           )

       def batch_classify(self, cookies: List[Cookie]) -> List[ClassificationResult]:
           # Vectorized batch processing
           pass
   ```

2. **Modify cookie_scanner.py**
   - Add ML classification step
   - Implement hybrid strategy:
     ```python
     def classify_cookie(cookie):
         # 1. Check database override (highest priority)
         if db_result := get_db_classification(cookie):
             return db_result

         # 2. Try ML classifier
         ml_result = ml_classifier.classify(cookie)
         if ml_result.confidence >= 0.75:  # High confidence threshold
             return ml_result

         # 3. Fallback to IAB GVL
         if iab_result := get_iab_classification(cookie):
             return iab_result

         # 4. Fallback to rules
         if rules_result := get_rules_classification(cookie):
             # Blend ML + rules if ML confidence moderate (0.4-0.75)
             if 0.4 <= ml_result.confidence < 0.75:
                 return blend_predictions(ml_result, rules_result)
             return rules_result

         # 5. Return ML prediction with low confidence flag
         return ml_result
     ```

3. **Add confidence & evidence fields**
   - Update Cookie model:
     ```python
     class Cookie(BaseModel):
         # ... existing fields ...
         ml_confidence: Optional[float] = None
         ml_probabilities: Optional[Dict[str, float]] = None
         classification_source: str  # "DB", "ML_High", "ML_Low", "IAB", "Rules"
         classification_evidence: Optional[List[str]] = None  # Explain why
     ```

4. **Implement explainability**
   ```python
   # ml_classifier/explainability.py
   def generate_evidence(cookie, prediction):
       evidence = []

       # Top 3 features that influenced decision
       feature_importance = get_feature_importance(cookie)
       for feature, importance in feature_importance[:3]:
           evidence.append(f"{feature}: {importance:.2%} influence")

       # Human-readable explanation
       if prediction.category == "Analytics":
           if cookie.domain in ANALYTICS_DOMAINS:
               evidence.append(f"Domain '{cookie.domain}' is known analytics vendor")
           if "_ga" in cookie.name:
               evidence.append("Cookie name matches Google Analytics pattern")

       return evidence
   ```

**Deliverables:**
- ✅ MLCookieClassifier integrated
- ✅ Hybrid classification strategy
- ✅ Confidence scores in scan results
- ✅ Evidence/reasoning displayed to admins

---

### Phase 4: Admin Interface (Week 4)
**Goal**: Build tools for model monitoring and feedback

1. **ML dashboard endpoint**
   ```python
   # api/routers/ml_admin.py
   @router.get("/ml/metrics")
   async def get_ml_metrics():
       return {
           "model_version": "1.0",
           "accuracy": 0.87,
           "last_trained": "2025-01-15",
           "predictions_count": 15234,
           "avg_confidence": 0.82,
           "low_confidence_count": 423,  # Needs review
           "category_distribution": {...}
       }

   @router.get("/ml/low-confidence")
   async def get_low_confidence_cookies(limit: int = 100):
       # Return cookies with confidence < 0.6 for admin review
       pass

   @router.post("/ml/feedback")
   async def submit_feedback(cookie_id: str, correct_category: str):
       # Store correction for retraining
       pass
   ```

2. **Annotation tool UI**
   - Simple web form for quick labeling
   - Bulk import from CSV
   - Export corrected labels

3. **Model performance monitoring**
   ```python
   # ml_classifier/monitoring.py
   class ModelMonitor:
       def track_prediction(self, cookie, prediction):
           # Log to analytics DB
           self.metrics.increment("predictions_total")
           self.metrics.histogram("confidence_score", prediction.confidence)
           self.metrics.increment(f"category_{prediction.category}")

       def detect_drift(self):
           # Compare feature distributions vs training data
           # Alert if significant drift detected
           pass
   ```

**Deliverables:**
- ✅ Admin API endpoints for ML metrics
- ✅ Annotation tool for labeling
- ✅ Monitoring dashboard

---

### Phase 5: Model Improvement (Week 5-6)
**Goal**: Enhance accuracy through advanced techniques

1. **Ensemble modeling**
   - Combine Random Forest + XGBoost + Logistic Regression
   - Voting classifier for robust predictions

2. **Feature expansion**
   - Add NLP features from cookie names:
     - TF-IDF on character n-grams
     - Word embeddings (Word2Vec on cookie names)
   - Network-based features:
     - Domain reputation scores
     - Vendor co-occurrence patterns

3. **Active learning loop**
   - Weekly retraining with admin feedback
   - Prioritize uncertain samples for labeling

4. **Model versioning**
   ```python
   # ml_classifier/model_registry.py
   class ModelRegistry:
       def register_model(self, model, version, metrics):
           pass

       def get_model(self, version="latest"):
           pass

       def ab_test(self, model_a, model_b, traffic_split=0.5):
           # Route 50% to each model, compare metrics
           pass
   ```

**Deliverables:**
- ✅ Ensemble model with >90% accuracy
- ✅ Advanced features (NLP, network)
- ✅ Model registry for versioning
- ✅ A/B testing framework

---

## Confidence Scoring & Evidence System

### Confidence Levels
```python
HIGH_CONFIDENCE = 0.75-1.0      # Use ML prediction
MEDIUM_CONFIDENCE = 0.50-0.75   # Blend with rules, flag for review
LOW_CONFIDENCE = 0.0-0.50       # Use fallback, prioritize for manual review
```

### Evidence Generation
For each prediction, provide 3-5 evidence points:

**Example 1: High Confidence Analytics**
```json
{
  "cookie_name": "_ga",
  "domain": ".google-analytics.com",
  "predicted_category": "Analytics",
  "confidence": 0.94,
  "source": "ML_Model_v1.2",
  "evidence": [
    "Domain '.google-analytics.com' is known Google Analytics vendor (100% match)",
    "Cookie name '_ga' matches analytics pattern (feature importance: 45%)",
    "Duration '730 days' typical for analytics cookies (feature importance: 18%)",
    "Third-party cookie with 'None' SameSite (common for tracking)",
    "Set after consent acceptance (compliance indicator)"
  ]
}
```

**Example 2: Low Confidence Unknown**
```json
{
  "cookie_name": "xfz_98kj",
  "domain": ".unknown-adtech.io",
  "predicted_category": "Advertising",
  "confidence": 0.42,
  "source": "ML_Model_Fallback",
  "evidence": [
    "Third-party cookie suggests tracking purpose (feature importance: 32%)",
    "Long duration '365 days' common for ads (feature importance: 22%)",
    "Domain not in known vendor database (low confidence)",
    "High name entropy '0.89' suggests tracking ID (feature importance: 15%)"
  ],
  "admin_action_required": true,
  "suggested_category": "Advertising",
  "alternative_categories": {
    "Advertising": 0.42,
    "Analytics": 0.31,
    "Functionality": 0.18,
    "Necessary": 0.09
  }
}
```

---

## Data Requirements

### Minimum Dataset Sizes
- **Initial training**: 5,000 labeled cookies (bootstrap from rules + public datasets)
- **Production deployment**: 10,000+ labeled cookies
- **High accuracy (>90%)**: 25,000+ labeled cookies
- **Per-category minimum**: 500 samples each to avoid class imbalance

### Dataset Balance
```
Strictly Necessary:  20% (e.g., sessionid, csrf_token)
Functionality:       15% (e.g., language, theme)
Analytics:           35% (e.g., _ga, _gid, _hjid) ← Most common
Advertising:         30% (e.g., _fbp, IDE, test_cookie)
```

### Data Quality Criteria
- No duplicate cookie names per domain
- Verified labels (manual review or high-confidence sources)
- Diverse domain coverage (not just Google/Facebook)
- Temporal diversity (cookies from different eras)

---

## Performance Targets

### Model Metrics
- **Overall Accuracy**: ≥85% (baseline), ≥90% (production)
- **Per-Class F1-Score**: ≥0.80 for all categories
- **Precision (Necessary)**: ≥0.95 (critical for compliance)
- **Recall (Advertising)**: ≥0.90 (important for user privacy)

### Operational Metrics
- **Inference Time**: <1ms per cookie, <100ms for batch of 500
- **Model Size**: <50MB (for fast loading)
- **Confidence Coverage**: ≥75% of predictions with confidence >0.75
- **Manual Review Rate**: <10% of cookies flagged for admin review

### System Integration
- **Scan Performance Impact**: <5% slowdown vs rule-based
- **Memory Overhead**: <200MB for loaded model
- **API Response Time**: No degradation

---

## Risk Mitigation

### Risks & Mitigation Strategies

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Insufficient training data | Low accuracy | Bootstrap from rules, scrape public datasets, synthetic data |
| Model overfitting | Poor generalization | Cross-validation, regularization, ensemble methods |
| Concept drift (new cookie types) | Degrading accuracy | Continuous monitoring, monthly retraining, active learning |
| Slow inference | Scan performance hit | Model optimization (ONNX), batch processing, caching |
| Imbalanced classes | Biased predictions | Class weighting, oversampling (SMOTE), stratified sampling |
| Adversarial cookies | Misclassification | Anomaly detection, manual review queue, confidence thresholds |

### Fallback Strategy
Always maintain hybrid approach:
```
ML (high confidence) → IAB GVL → Rules → ML (low confidence with warning)
```

---

## Success Criteria

### MVP (Minimum Viable Product) - Week 3
- ✅ Random Forest classifier with ≥85% accuracy
- ✅ Integrated into cookie scanner with confidence scores
- ✅ Evidence generation for top 3 features
- ✅ 5,000+ labeled training samples
- ✅ Admin API for low-confidence review

### Production Ready - Week 6
- ✅ Model accuracy ≥90% on test set
- ✅ Ensemble model (RF + XGBoost)
- ✅ 10,000+ labeled training samples
- ✅ Active learning pipeline for continuous improvement
- ✅ Monitoring dashboard with drift detection
- ✅ A/B testing framework for model versions
- ✅ Comprehensive evidence explanations

### Future Enhancements (Post-MVP)
- Deep learning model for complex patterns (BERT for cookie names)
- Transfer learning from pre-trained privacy models
- Multi-lingual support (non-English cookie names)
- Automated vendor detection from network traffic
- Real-time model updates (online learning)

---

## Technology Stack Summary

### Core ML Libraries
```python
scikit-learn==1.5.0      # Random Forest, Logistic Regression, preprocessing
xgboost==2.0.3           # Gradient boosting
lightgbm==4.3.0          # Alternative gradient boosting
pandas==2.2.0            # Data manipulation
numpy==1.26.3            # Numerical operations
```

### Model Interpretability
```python
shap==0.44.0             # SHAP values for feature importance
matplotlib==3.8.2        # Visualization
seaborn==0.13.0          # Statistical plots
```

### Model Deployment
```python
joblib==1.3.2            # Model serialization
onnx==1.15.0             # Cross-platform model format
onnxruntime==1.17.0      # Fast ONNX inference
```

### Data Collection
```python
requests==2.31.0         # API calls for public datasets
beautifulsoup4==4.12.0   # Web scraping (if needed)
```

**Total Dependencies**: ~10 packages, all open-source, no external API calls

---

## Timeline Overview

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | Foundation | ML structure, feature extractor, 1,000 labeled cookies |
| 2 | Training | Random Forest v1.0, 85% accuracy, model artifacts |
| 3 | Integration | MLCookieClassifier, hybrid strategy, confidence scores |
| 4 | Admin Tools | ML dashboard, annotation tool, monitoring |
| 5-6 | Improvement | Ensemble model, 90% accuracy, active learning, A/B testing |

**Total Time**: 6 weeks for production-ready ML classifier

---

## Next Steps

1. **Approve Plan**: Review and sign off on architecture
2. **Setup Environment**: Create `ml_classifier/` module structure
3. **Data Collection**: Execute bootstrap script for initial training data
4. **Begin Phase 1**: Implement FeatureExtractor class
5. **Weekly Check-ins**: Review progress, adjust priorities

---

## Questions for Stakeholders

1. **Accuracy vs Speed**: Acceptable trade-off? (90% accuracy may need 10,000+ samples)
2. **Category Granularity**: Use 4 categories (Necessary, Functionality, Analytics, Advertising) or keep existing 6?
3. **Admin Bandwidth**: How many cookies/week can admins label? (Determines active learning speed)
4. **Compliance Priority**: Should "Necessary" precision be >95% even if overall accuracy drops slightly?
5. **Deployment**: Weekly model retraining acceptable, or prefer manual approval?

---

## Appendix: Alternatives Considered

### Why Not Neural Networks?
- **Pros**: Can learn complex patterns, high accuracy potential
- **Cons**: Requires 50,000+ samples, slow training, overfitting risk, black-box interpretability
- **Decision**: Use for future enhancement after gathering more data

### Why Not Pre-trained LLMs?
- **Pros**: Zero-shot classification, handles novel cookies well
- **Cons**: External API dependency (OpenAI, Anthropic), cost, latency, privacy concerns
- **Decision**: Explicitly prohibited per requirements

### Why Not Rule-Based Only?
- **Pros**: Deterministic, interpretable, fast
- **Cons**: Cannot generalize, requires manual updates, poor with novel cookies
- **Decision**: Keep as fallback, augment with ML

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Author**: Claude (Sonnet 4.5)
**Status**: Awaiting Approval
