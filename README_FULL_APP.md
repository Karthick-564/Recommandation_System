# LightFM Volunteer Matching System - Complete Web Application

## 🎯 Overview
This is a **fully functional** Flask web application that uses the LightFM recommendation engine to match students with volunteer opportunities. Unlike the previous demo versions, this application includes real machine learning model training, user authentication, and dynamic recommendations.

## 🚀 Quick Start

### Option 1: Double-click to Run
```
Double-click: launch_full_app.bat
```

### Option 2: Manual Command Line
```bash
cd d:\hackathon
python full_app.py
```

## 📋 System Requirements
- Python 3.8 or higher
- Required packages: Flask, LightFM, pandas, numpy, scikit-learn

## 🔧 Architecture

### Core Components
1. **full_app.py** - Main Flask application with real LightFM training
2. **VolunteerRecommendationSystem** - Complete ML pipeline class
3. **CSV Data Files** - Student profiles, opportunities, and interactions
4. **Templates** - Professional HTML interfaces with Tailwind CSS

### Machine Learning Pipeline
```
CSV Data → Feature Engineering → LightFM Model → Matrix Factorization → Recommendations
```

## 📊 Data Structure

### Students (students.csv)
- 100 student profiles with skills, interests, availability
- Features: skills, interests, willingness_level, work_calendar

### Opportunities (opportunities.csv)  
- 100 volunteer opportunities from various NGOs
- Features: required_skills, description, work_calendar, importance_level

### Interactions (interactions.csv)
- 671 student-opportunity interactions with ratings
- Used for collaborative filtering training

## 🤖 LightFM Model Details

### Algorithm Configuration
- **Loss Function**: WARP (Weighted Approximate-Rank Pairwise)
- **Components**: 50 latent factors
- **Learning Rate**: 0.05
- **Epochs**: 10
- **Regularization**: L2 with lambda=0.01

### Features Used
- **User Features**: Skills, interests, commitment level, availability
- **Item Features**: Required skills, organization type, urgency level
- **Hybrid Approach**: Combines collaborative and content-based filtering

## 🌐 Web Application Features

### Authentication System
- Student login interface
- Session management
- Secure user routing

### Dashboard Features
- Real-time LightFM model training status
- Personalized recommendations with match percentages
- Interactive profile display
- Apply/Save/Share functionality for opportunities

### API Endpoints
- `GET /` - Landing page with model initialization
- `POST /login` - User authentication
- `GET /dashboard` - Student dashboard
- `GET /get_recommendations` - Dynamic recommendation API
- `GET /logout` - Session termination

## 🎨 Frontend Technology
- **CSS Framework**: Tailwind CSS 3.0
- **Icons**: Font Awesome 6.0
- **JavaScript**: Vanilla JS with async/await
- **Design**: Responsive, professional interface

## 🔍 Key Differences from Demo Versions

### Real Machine Learning
- **Before**: Static sample data and hardcoded recommendations
- **Now**: Live LightFM model training with actual matrix factorization

### Dynamic Features  
- **Before**: Fixed demo content
- **Now**: Personalized recommendations based on user profile

### Production Architecture
- **Before**: Single HTML file
- **Now**: Full Flask application with proper routing and sessions

## 📈 Performance Metrics

### Model Training
- Training Time: ~30-60 seconds (first launch)
- Data Processing: 671 interactions, 100 users, 100 items
- Feature Matrix: 200+ encoded features

### Recommendation Quality
- Top-K Recommendations: 5 per user
- Scoring: LightFM prediction scores converted to percentages
- Ranking: Sorted by prediction confidence

## 🛠️ Troubleshooting

### Common Issues

**Port 5000 already in use:**
```bash
# Kill existing process
netstat -ano | findstr :5000
taskkill /PID [PID_NUMBER] /F
```

**Missing dependencies:**
```bash
pip install flask lightfm pandas numpy scikit-learn
```

**Model training timeout:**
- First launch takes time for LightFM training
- Subsequent launches use cached model (faster)

**Template not found:**
- Ensure templates/ directory exists
- Verify index.html and student_dashboard.html are present

## 📁 File Structure
```
d:\hackathon/
├── full_app.py                     # Main Flask application
├── launch_full_app.bat             # Windows launcher
├── students.csv                    # Student profiles
├── opportunities.csv               # Volunteer opportunities  
├── interactions.csv                # Training interactions
├── templates/
│   ├── index.html                  # Login page
│   └── student_dashboard_new.html  # Dashboard interface
└── README.md                       # This documentation
```

## 🎯 Next Steps

### For Development
1. **Database Integration**: Replace CSV with PostgreSQL/MySQL
2. **User Registration**: Add signup functionality  
3. **NGO Dashboard**: Interface for organizations to post opportunities
4. **Real-time Notifications**: WebSocket integration for instant updates
5. **Mobile App**: React Native companion app

### For Production
1. **Cloud Deployment**: AWS/Heroku deployment
2. **Load Balancing**: Handle multiple concurrent users
3. **Model Versioning**: A/B test different recommendation algorithms
4. **Analytics Dashboard**: Track recommendation performance

## 🚀 Launch Instructions

1. **Navigate to folder**: `cd d:\hackathon`
2. **Run launcher**: Double-click `launch_full_app.bat`
3. **Wait for training**: Model initialization takes ~60 seconds
4. **Open browser**: Go to `http://localhost:5000`
5. **Login as student**: Use any student ID (1-100)
6. **View recommendations**: Real LightFM predictions displayed

## ✅ Success Indicators

When working correctly, you should see:
- ✅ "LightFM model trained successfully" in console
- ✅ Login page loads at localhost:5000
- ✅ Student dashboard with personalized recommendations  
- ✅ Match percentages and prediction scores
- ✅ Interactive apply/save/share buttons

## 📞 Support

If you encounter issues:
1. Check console output for error messages
2. Verify all CSV files are present and readable
3. Ensure Python 3.8+ with required packages
4. Try restarting the application

---

**This is your fully functional LightFM recommendation system - no more demos!** 🎉