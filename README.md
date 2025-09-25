# LightFM Volunteer Recommendation System - Complete Web Application

## 🎯 Project Overview

This project creates a complete volunteer recommendation system using LightFM (Light Factorization Machines) with a Flask web interface. The system matches students with volunteer opportunities based on their skills, interests, and availability.

## 📁 Project Structure

```
d:\hackathon\
├── app.py                           # Flask web application (main server)
├── working_lightfm_demo.py         # LightFM model implementation (fixed version)
├── test_app.py                      # Testing script for the application
├── students.csv                     # Sample student data (100 students)
├── opportunities.csv                # Sample volunteer opportunities (100 opportunities)  
├── interactions.csv                 # Sample interaction data (671 interactions)
└── templates/
    ├── index.html                   # Login page (student/NGO authentication)
    ├── student_dashboard.html       # Student recommendation interface
    └── ngo_dashboard.html          # NGO opportunity posting interface
```

## 🚀 How to Run the Application

### Prerequisites
- Python 3.8+ with Conda
- Required packages: Flask, LightFM, pandas, numpy, scikit-learn

### Step 1: Test the Application
```bash
python test_app.py
```
This will verify all components are working correctly.

### Step 2: Start the Flask Server
```bash
python app.py
```

### Step 3: Access the Web Interface
Open your browser and go to: **http://localhost:5000**

## 🌟 Features

### For Students:
- 🔐 **Login Interface**: Secure authentication system
- 🎯 **Personalized Recommendations**: Get top 5 volunteer opportunities matched to your skills
- 🏷️ **Skill Matching**: See which of your skills match each opportunity
- 📊 **Recommendation Scores**: View confidence scores for each match
- 🎨 **Modern UI**: Responsive design with Tailwind CSS

### For NGOs:
- 🔐 **NGO Portal**: Dedicated interface for organizations
- ➕ **Post Opportunities**: Easy form to add new volunteer positions
- 🔧 **Skill Requirements**: Specify required skills for better matching
- ⚡ **Priority Levels**: Set importance levels (standard/high/emergency)
- 📅 **Schedule Management**: Define available days for volunteers

## 🤖 Technical Implementation

### LightFM Model Features:
- **Collaborative Filtering**: Learns from student-opportunity interactions
- **Content-Based Filtering**: Uses student skills and opportunity requirements
- **Matrix Factorization**: WARP loss function for ranking optimization
- **Feature Engineering**: Skills, interests, and availability matching

### Data Processing:
- **100 Students**: Diverse skills (Python, C++, Teaching, Marketing, etc.)
- **100 Opportunities**: Various NGO projects requiring different skill sets
- **671 Interactions**: Training data for the recommendation algorithm
- **Perfect Feature Alignment**: Skills perfectly match opportunity requirements

### Web Architecture:
- **Flask Backend**: RESTful API with recommendation endpoints
- **HTML Templates**: Jinja2 templating with Tailwind CSS styling
- **JavaScript Frontend**: Dynamic content loading and form handling
- **CSV Data Storage**: Simple file-based data persistence

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Login page |
| `/login` | POST | Authentication |
| `/student-dashboard` | GET | Student recommendation interface |
| `/ngo-dashboard` | GET | NGO opportunity posting interface |
| `/get-recommendations` | GET | Get recommendations for student |
| `/add_opportunity` | POST | Add new volunteer opportunity |

## 📊 Recommendation Algorithm

The system uses LightFM with the following approach:

1. **Data Preparation**: 
   - Student-opportunity interaction matrix
   - Feature vectors for skills, interests, availability

2. **Model Training**:
   - WARP loss for ranking optimization
   - 30-50 components for latent factors
   - Feature-based matrix factorization

3. **Recommendation Generation**:
   - Personalized scoring for each student
   - Top-K filtering (default: 5 recommendations)
   - Skill-based explanations for matches

## 🎨 User Experience

### Student Flow:
1. **Login** → Enter student ID on main page
2. **Dashboard** → View personalized recommendations
3. **Matching** → See skill compatibility and scores
4. **Selection** → Choose opportunities that match interests

### NGO Flow:
1. **Login** → Select NGO option on main page  
2. **Post Opportunity** → Fill out detailed form
3. **Skill Specification** → Define required skills
4. **Automatic Matching** → System matches with students

## 🔍 Testing & Validation

Run the test script to verify:
- ✅ Flask application imports successfully
- ✅ All data files are present
- ✅ HTML templates are available
- ✅ Recommendation system initializes correctly

## 🚀 Next Steps

To enhance the system further:
- Add user registration and authentication
- Implement opportunity bookmarking
- Add email notifications for matches
- Create analytics dashboard for NGOs
- Integrate with external volunteer databases

## 🎉 Success Metrics

The system successfully addresses the original requirements:
- ✅ **LightFM Implementation**: Working recommendation model
- ✅ **Sample Data**: Comprehensive CSV datasets
- ✅ **Web Interface**: Complete Flask application
- ✅ **User Experience**: Intuitive dashboards for both user types
- ✅ **Recommendation Output**: Fixed the "no recommendations" issue

---

**Ready to make a difference! 🌟 Students and NGOs can now connect through intelligent volunteer matching.**