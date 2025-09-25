#!/usr/bin/env python3
"""
Test script to verify Flask application functionality
"""

def test_flask_app():
    """Test if our Flask app can be imported and runs correctly"""
    try:
        from app import app, RecommendationSystem
        print("✅ Flask app imported successfully!")
        
        # Test routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.rule} -> {rule.endpoint}")
        
        print("\n📍 Available Routes:")
        for route in routes:
            print(f"  {route}")
        
        # Test recommendation system
        try:
            rec_system = RecommendationSystem()
            print("\n🤖 RecommendationSystem class created successfully!")
            print(f"   Data files path: {rec_system.data_path}")
            return True
        except Exception as e:
            print(f"\n❌ Error creating RecommendationSystem: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error importing Flask app: {e}")
        return False

def test_data_files():
    """Test if our CSV data files exist"""
    import os
    
    data_files = [
        'students.csv',
        'opportunities.csv', 
        'interactions.csv'
    ]
    
    print("\n📄 Data Files Check:")
    all_exist = True
    for file in data_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (missing)")
            all_exist = False
    
    return all_exist

def test_templates():
    """Test if template files exist"""
    import os
    
    template_files = [
        'templates/index.html',
        'templates/student_dashboard.html',
        'templates/ngo_dashboard.html'
    ]
    
    print("\n🎨 Template Files Check:")
    all_exist = True
    for file in template_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (missing)")
            all_exist = False
    
    return all_exist

if __name__ == "__main__":
    print("🔍 Testing Flask LightFM Recommendation System")
    print("=" * 50)
    
    # Run tests
    flask_ok = test_flask_app()
    data_ok = test_data_files()
    templates_ok = test_templates()
    
    print("\n📊 Test Summary:")
    print("=" * 30)
    print(f"Flask App:     {'✅ PASS' if flask_ok else '❌ FAIL'}")
    print(f"Data Files:    {'✅ PASS' if data_ok else '❌ FAIL'}")
    print(f"Templates:     {'✅ PASS' if templates_ok else '❌ FAIL'}")
    
    if flask_ok and data_ok and templates_ok:
        print("\n🎉 All tests passed! Ready to run the Flask app.")
        print("\n🚀 To start the web application:")
        print("   python app.py")
        print("\n🌐 Then open your browser to:")
        print("   http://localhost:5000")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")