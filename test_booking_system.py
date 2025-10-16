#!/usr/bin/env python3
"""
Test script to verify the booking system functionality
"""

import requests
import json
import time

def test_booking_system():
    """Test the booking system endpoints"""
    base_url = "http://localhost:5000"

    print("🔍 Testing Volunteer Matching Platform Booking System")
    print("=" * 60)

    # Test 1: Check if server is running
    print("\n1. Testing server connectivity...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Server is running and responding")
        else:
            print(f"❌ Server responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

    # Test 2: Student login
    print("\n2. Testing student login...")
    try:
        login_data = {
            "name": "Test Student",
            "email": "student0@example.com",
            "user_type": "student",
            "student_id": 0
        }
        response = requests.post(f"{base_url}/api/login", json=login_data)
        if response.status_code == 200:
            login_result = response.json()
            if login_result.get('success'):
                student_id = login_result['user_id']
                print(f"✅ Student login successful (ID: {student_id})")
            else:
                print(f"❌ Student login failed: {login_result.get('message')}")
                return False
        else:
            print(f"❌ Login endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Login test error: {e}")
        return False

    # Test 3: Get recommendations
    print("\n3. Testing recommendations...")
    try:
        response = requests.get(f"{base_url}/api/recommendations/{student_id}")
        if response.status_code == 200:
            recommendations = response.json()
            if isinstance(recommendations, list) and len(recommendations) > 0:
                print(f"✅ Got {len(recommendations)} recommendations")
                # Get first opportunity ID for testing
                first_rec = recommendations[0]
                opportunity_id = first_rec.get('opportunity_id', 0)
                print(f"   First recommendation: {first_rec.get('ngo_name', 'Unknown')}")
            else:
                print("❌ No recommendations received")
                return False
        else:
            print(f"❌ Recommendations endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Recommendations test error: {e}")
        return False

    # Test 4: Get available slots for an opportunity
    print("\n4. Testing available slots retrieval...")
    try:
        response = requests.get(f"{base_url}/api/slots/{opportunity_id}")
        if response.status_code == 200:
            slots = response.json()
            if isinstance(slots, list) and len(slots) > 0:
                print(f"✅ Got {len(slots)} available slots")
                # Get first available slot
                available_slots = [s for s in slots if s.get('available_spots', 0) > 0]
                if available_slots:
                    first_slot = available_slots[0]
                    slot_id = first_slot['slot_id']
                    print(f"   First available slot: ID {slot_id} on {first_slot['date']} at {first_slot['start_time']}")
                else:
                    print("❌ No available slots found")
                    return False
            else:
                print("❌ No slots received")
                return False
        else:
            print(f"❌ Slots endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slots test error: {e}")
        return False

    # Test 5: Book a slot
    print("\n5. Testing slot booking...")
    try:
        # Find an available slot that hasn't been booked yet
        available_slots = [s for s in slots if s.get('available_spots', 0) > 0]
        if not available_slots:
            print("❌ No available slots found for booking test")
            return False

        # Use a different slot than the ones already booked by student 0
        # Student 0 has booked slot 1 (from bookings.csv)
        booked_slots = [1]  # Student 0's existing bookings
        test_slot = None
        for slot in available_slots:
            if slot['slot_id'] not in booked_slots:
                test_slot = slot
                break

        if not test_slot:
            print("❌ No alternative available slots found")
            return False

        slot_id = test_slot['slot_id']
        print(f"   Using slot ID {slot_id} for booking test")

        booking_data = {
            "student_id": student_id,
            "slot_id": slot_id,
            "notes": "Test booking via automated test"
        }
        response = requests.post(f"{base_url}/api/book", json=booking_data)
        if response.status_code == 200:
            booking_result = response.json()
            if booking_result.get('success'):
                booking_id = booking_result.get('booking_id')
                print(f"✅ Booking successful (ID: {booking_id})")
            else:
                print(f"❌ Booking failed: {booking_result.get('message')}")
                return False
        else:
            print(f"❌ Booking endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Booking test error: {e}")
        return False

    # Test 6: Get student's bookings
    print("\n6. Testing booking retrieval...")
    try:
        response = requests.get(f"{base_url}/api/my-bookings/{student_id}")
        if response.status_code == 200:
            bookings = response.json()
            if isinstance(bookings, list) and len(bookings) > 0:
                print(f"✅ Retrieved {len(bookings)} bookings")
                latest_booking = bookings[-1]  # Most recent booking
                print(f"   Latest booking: {latest_booking.get('ngo_name')} on {latest_booking.get('date')}")
            else:
                print("❌ No bookings found")
                return False
        else:
            print(f"❌ My bookings endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bookings retrieval test error: {e}")
        return False

    # Test 7: Try to book the same slot again (should fail)
    print("\n7. Testing double booking prevention...")
    try:
        booking_data = {
            "student_id": student_id,
            "slot_id": slot_id,
            "notes": "Attempted double booking"
        }
        response = requests.post(f"{base_url}/api/book", json=booking_data)
        if response.status_code == 200:
            booking_result = response.json()
            if not booking_result.get('success'):
                print("✅ Double booking correctly prevented")
                print(f"   Message: {booking_result.get('message')}")
            else:
                print("❌ Double booking was allowed (should have been prevented)")
                return False
        else:
            print(f"❌ Double booking test endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Double booking test error: {e}")
        return False

    # Test 8: Student registration
    print("\n8. Testing student registration...")
    try:
        register_data = {
            "name": "Test New Student",
            "email": f"test_student_{int(time.time())}@example.com",
            "skills": "programming, communication",
            "interests": "education, technology",
            "university": "Test University"
        }
        response = requests.post(f"{base_url}/api/register", json=register_data)
        if response.status_code == 200:
            register_result = response.json()
            if register_result.get('success'):
                new_student_id = register_result.get('user_id')
                print(f"✅ Registration successful (New ID: {new_student_id})")
            else:
                print(f"❌ Registration failed: {register_result.get('message')}")
                return False
        else:
            print(f"❌ Registration endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Registration test error: {e}")
        return False

    # Test 9: NGO opportunity posting
    print("\n9. Testing NGO opportunity posting...")
    try:
        opportunity_data = {
            "ngo_name": "Test NGO",
            "description": "Test volunteer opportunity for automated testing",
            "required_skills": "organization, communication",
            "importance_level": "medium",
            "work_calendar": "Flexible, 2-4 hours per week"
        }
        response = requests.post(f"{base_url}/api/opportunities", json=opportunity_data)
        if response.status_code == 200:
            opp_result = response.json()
            if opp_result.get('success'):
                new_opp_id = opp_result.get('opportunity_id')
                print(f"✅ Opportunity posted successfully (ID: {new_opp_id})")
            else:
                print(f"❌ Opportunity posting failed: {opp_result.get('message')}")
                return False
        else:
            print(f"❌ Opportunity posting endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Opportunity posting test error: {e}")
        return False

    print("\n" + "=" * 60)
    print("🎉 ALL BOOKING SYSTEM TESTS PASSED!")
    print("=" * 60)
    print("\n✅ Server connectivity")
    print("✅ Student login")
    print("✅ Recommendations retrieval")
    print("✅ Available slots retrieval")
    print("✅ Slot booking")
    print("✅ Booking retrieval")
    print("✅ Double booking prevention")
    print("✅ Student registration")
    print("✅ NGO opportunity posting")
    print("\n🚀 The booking system is working correctly!")
    print("🌐 You can now test the web interface at: http://localhost:5000")

    return True

if __name__ == "__main__":
    success = test_booking_system()
    if not success:
        print("\n❌ Some tests failed. Check the errors above.")
        exit(1)
