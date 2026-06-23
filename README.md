# ASTRAM CongestionIQ

**Predict Traffic Disruptions Before They Happen**

ASTRAM CongestionIQ is an AI-powered traffic intelligence platform that transforms real-world events into actionable traffic operations insights. Instead of reacting to congestion after it occurs, ASTRAM predicts disruptions in advance using news intelligence, geospatial analysis, and machine learning.

---

## Problem Statement

Modern traffic management systems are largely reactive:

* Congestion is addressed only after it occurs.
* News events, accidents, protests, and public gatherings are not integrated into traffic operations.
* Resource deployment such as officers and barricades is inefficient without predictive intelligence.
* Traffic teams lack a unified platform to anticipate and mitigate disruptions.

---

## Solution

ASTRAM CongestionIQ provides an end-to-end predictive traffic intelligence pipeline:

1. **Ingest** real-time news and RSS feeds.
2. **Analyze** unstructured event information using NLP.
3. **Geo-map** events to road corridors and traffic zones.
4. **Predict** traffic impact using ML models.
5. **Recommend** operational actions through an interactive dashboard.

The platform enables city authorities to proactively manage traffic before congestion escalates.

---

## Key Features

### Live Event Intelligence

* Continuous ingestion of news and RSS feeds.
* Automatic extraction of event type, location, severity, and timing.

### Predictive Traffic Analytics

* Forecast incident volumes.
* Predict road closures.
* Estimate congestion hotspots.
* Evaluate event impact scores.

### Route Diversion Engine

* Alternative route generation using Mappls APIs.
* Real-time travel distance and duration estimation.

### Cascade Studio

* Simulate traffic scenarios.
* Analyze how one disruption impacts nearby corridors.
* Evaluate visitor surge effects on road networks.

### Resource Deployment Planning

* Officer deployment recommendations.
* Barricade placement suggestions.
* Emergency corridor planning.

### Explainable AI

* Displays important model drivers.
* Provides transparent prediction reasoning for operators.

---

## System Architecture

```text
News/RSS Feeds
       │
       ▼
News Scraper
       │
       ▼
Event Normalization
       │
       ▼
Geo-Mapping Engine
       │
       ▼
Machine Learning Models
       │
       ▼
Mappls Routing Engine
       │
       ▼
Traffic Operations Dashboard
```

---

## Machine Learning Models

| Model                       | Purpose                       | Algorithm                 |
| --------------------------- | ----------------------------- | ------------------------- |
| Incident Volume Forecasting | Predict incident count        | LightGBM                  |
| Road Closure Prediction     | Closure classification        | Random Forest + SMOTE     |
| Officer Deployment          | Resource recommendation       | Gradient Boosting         |
| Barricade Deployment        | Resource recommendation       | Gradient Boosting         |
| Hotspot Risk Prediction     | Congestion risk estimation    | LightGBM                  |
| Duration Prediction         | Event duration estimation     | LightGBM                  |
| Impact Score Prediction     | Event impact assessment       | LightGBM                  |
| Cascade Modeling            | Corridor propagation analysis | Markov Chain              |
| Parking Overflow Detection  | Parking demand prediction     | Logistic Regression / GBM |
| Green Corridor Routing      | Emergency route optimization  | Dijkstra Graph Algorithm  |

---

## Dataset

### Traffic Incident Dataset

* 8,173 anonymized Bengaluru traffic incidents
* Temporal features:

  * Hour
  * Weekday
  * Month
* Location features:

  * Zone
  * Corridor
  * Junction
* Context features:

  * Event Type
  * Priority
  * Closure Flag

### Feature Engineering

* Label Encoding
* Missing Value Imputation
* Duration Extraction
* Corridor-Based Aggregation
* Impact Score Generation

---

## Tech Stack

### Frontend

* Next.js
* React
* Interactive Dashboard
* Real-Time Polling

### Backend

* Flask
* REST APIs
* Blueprint Architecture
* Authentication & Token Management

### Machine Learning

* Scikit-learn
* LightGBM
* Random Forest
* Gradient Boosting
* Joblib

### Geospatial Intelligence

* Mappls (MapmyIndia)
* Route Geometry
* Polyline Decoding
* Corridor Mapping

### Deployment

* Render.com
* CI/CD Auto Deployment
* Separate Frontend and Backend Services

---

## API Endpoints

### Health Check

```http
GET /api/health
```

### News Feed

```http
GET /api/news
```

### Prediction Service

```http
POST /api/predict
```

### Mappls Token

```http
GET /api/mappls/token
```

---

## Performance Metrics

| Metric                    | Score |
| ------------------------- | ----- |
| Road Closure Accuracy     | 91.2% |
| Parking Overflow Accuracy | 97.7% |
| Hotspot Risk R²           | 0.89  |
| Incident Volume R²        | 0.84  |
| Impact Score R²           | 0.99* |

*Impact Score model is currently under audit for potential feature leakage and will be retrained in future versions.

---

## Future Roadmap

### Q1

* Live sensor integration
* Traffic camera connectivity

### Q2

* Expansion to Delhi, Mumbai, and Chennai

### Q3

* Advanced duration classification
* Model audit completion

### Q4

* Continuous retraining pipeline
* Feedback-driven optimization

---

## Why ASTRAM?

### News → Intelligence

Transforms unstructured event information into traffic intelligence.

### City-Specific Predictions

Built using real Bengaluru traffic incident data.

### Operations Ready

Provides actionable recommendations rather than raw analytics.

---

## Team

* Nihaarika
* Pearl Rubyth Thomas
* Sai Krisha D

---

## Vision

ASTRAM CongestionIQ aims to become the predictive intelligence layer for smart city traffic operations by helping authorities:

* Predict congestion before it occurs
* Optimize resource deployment
* Improve emergency response
* Enhance urban mobility

**Predict. Prepare. Respond. Learn.**
