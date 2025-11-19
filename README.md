# Dynamic Cookie Scanner

ML-powered cookie classification and scanning system with advanced scheduling and analytics.

## 📁 Project Structure

```
dynamic_cookie_scanning_sep29/
├── src/                      # Main source code
│   ├── api/                  # FastAPI routers and endpoints
│   ├── core/                 # Core configuration and setup
│   ├── models/              # Database models (SQLAlchemy)
│   ├── services/            # Business logic services
│   ├── analytics/           # Analytics and reporting
│   ├── ml_classifier/       # ML classification engine
│   ├── database/            # Database utilities and connections
│   └── cache/               # Redis caching layer
│
├── cli/                      # Command-line interface tools
│   ├── run_api.py           # Start the API server
│   ├── run_celery_worker.py # Start Celery worker
│   ├── run_celery_beat.py   # Start Celery beat scheduler
│   ├── run_migrations.py    # Run database migrations
│   └── main.py              # Main CLI entry point
│
├── scripts/                  # Utility scripts
│   ├── admin/               # Admin utilities
│   │   ├── create_admin_user.py
│   │   └── generate_dev_token.py
│   ├── migrations/          # Database migration SQL files
│   ├── ml/                  # ML training and testing scripts
│   │   ├── train_model.py
│   │   ├── test_classifier.py
│   │   └── bootstrap_training_data.py
│   ├── cookie_scanner.py    # Cookie scanning utilities
│   ├── enterprise_scanner.py
│   └── schedule_manager.py
│
├── tests/                    # Test suite
│   ├── integration/         # Integration tests
│   ├── performance/         # Performance tests
│   └── *.py                 # Unit tests
│
├── config/                   # Configuration files
│   ├── config.py            # Main configuration
│   └── logger_setup.py      # Logging configuration
│
├── docker/                   # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.services.yml
│
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_ENDPOINTS_REFERENCE.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── ...
│
├── dashboard/                # Next.js dashboard (if applicable)
├── design/                   # Design files and assets
├── logs/                     # Application logs (gitignored)
├── results/                  # Scan results (gitignored)
├── training_data/           # ML training data (gitignored)
│
├── .gitignore
├── requirements.txt         # Python dependencies
├── setup.py                 # Package setup
└── README.md                # This file
```

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd dynamic_cookie_scanning_sep29
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# or
./install_dependencies.sh
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run database migrations:
```bash
python cli/run_migrations.py
```

### Running the Application

#### Start the API Server
```bash
python cli/run_api.py
```

#### Start Celery Worker
```bash
python cli/run_celery_worker.py
# or
./start_celery_worker.sh
```

#### Start Celery Beat Scheduler
```bash
python cli/run_celery_beat.py
```

### Using Docker

```bash
cd docker
docker-compose up -d
```

## 📚 Documentation

See the [docs](docs/) directory for comprehensive documentation:

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Endpoints Reference](docs/API_ENDPOINTS_REFERENCE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Quick Start Guide](docs/QUICK_START.md)
- [Contributing Guidelines](docs/CONTRIBUTING.md)

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/integration/
pytest tests/performance/

# Run with coverage
pytest --cov=src tests/
```

## 🔧 Development

### Creating Admin User
```bash
python scripts/admin/create_admin_user.py
```

### Training ML Model
```bash
python scripts/ml/train_model.py
```

### Running Scans
```bash
python scripts/cookie_scanner.py --url https://example.com
```

## 📦 Key Components

- **API**: FastAPI-based REST API
- **ML Classifier**: Cookie classification using scikit-learn
- **Celery**: Distributed task queue for async operations
- **PostgreSQL**: Primary database
- **Redis**: Caching and Celery broker
- **Dashboard**: Next.js-based web interface

## 🔒 Security

See [SECURITY_FEATURES_IMPLEMENTATION.md](docs/SECURITY_FEATURES_IMPLEMENTATION.md) for security features and best practices.

## 📊 Monitoring

Prometheus metrics are exposed at `/metrics`. See [PROMETHEUS_METRICS_GUIDE.md](docs/PROMETHEUS_METRICS_GUIDE.md) for details.

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution guidelines.

## 📄 License

[Your License Here]

## 📧 Support

For issues and questions, please open a GitHub issue or contact the development team.
