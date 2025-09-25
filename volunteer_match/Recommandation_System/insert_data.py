import psycopg2
import json

# ----------------------------
# 1️⃣ Connect to PostgreSQL
# ----------------------------
conn = psycopg2.connect(
    dbname='volunteer_match',    # your database
    user='YOUR_MAC_USERNAME',    # replace with your Mac username
    password='',                 # blank if local
    host='localhost'
)
cur = conn.cursor()

# ----------------------------
# 2️⃣ Helper function to enter list fields
# ----------------------------
def input_list(prompt):
    items = input(prompt + " (comma separated): ")
    return json.dumps([item.strip() for item in items.split(",")])

# ----------------------------
# 3️⃣ Insert a new student
# ----------------------------
def add_student():
    print("\n--- Enter New Student ---")
    name = input("Name: ")
    email = input("Email: ")
    password_hash = input("Password (or leave blank for 'hash123'): ") or "hash123"
    college = input("College: ")
    city = input("City: ")
    skills = input_list("Skills")
    interests = input_list("Interests")
    availability = input_list("Availability (e.g., Weekends, Evenings)")
    willingness_level = int(input("Willingness level (1-5): "))
    preferred_shift = input("Preferred shift (Short/Long/Flexible): ")
    language = input("Language: ")
    transport_access = input("Transport access? (y/n): ")
    transport_access = True if transport_access.lower() == 'y' else False

    cur.execute("""
        INSERT INTO students (name,email,password_hash,college,city,skills,interests,availability,willingness_level,preferred_shift,language,transport_access)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (name,email,password_hash,college,city,skills,interests,availability,willingness_level,preferred_shift,language,transport_access))

    conn.commit()
    print(f"Student {name} added successfully!\n")

# ----------------------------
# 4️⃣ Insert a new NGO
# ----------------------------
def add_ngo():
    print("\n--- Enter New NGO ---")
    name = input("NGO Name: ")
    email = input("NGO Email: ")
    password_hash = input("Password (or leave blank for 'hash123'): ") or "hash123"
    city = input("City: ")
    description = input("Description: ")

    cur.execute("""
        INSERT INTO ngos (name,email,password_hash,city,description)
        VALUES (%s,%s,%s,%s,%s)
    """, (name,email,password_hash,city,description))

    conn.commit()
    print(f"NGO {name} added successfully!\n")

# ----------------------------
# 5️⃣ Insert a new Opportunity
# ----------------------------
def add_opportunity():
    print("\n--- Enter New Opportunity ---")
    ngo_name = input("Which NGO (enter exact name): ")
    cur.execute("SELECT ngo_id FROM ngos WHERE name=%s", (ngo_name,))
    ngo = cur.fetchone()
    if not ngo:
        print("NGO not found! Please add NGO first.\n")
        return
    ngo_id = ngo[0]

    title = input("Opportunity Title: ")
    description = input("Description: ")
    required_skills = input_list("Required Skills")
    cause_type = input("Cause Type (Environment, Education, Health, etc.): ")
    city = input("City: ")
    urgency_level = int(input("Urgency level (1-5): "))
    importance_level = int(input("Importance level (1-5): "))
    shift_type = input("Shift Type (Short/Long/Remote): ")
    duration_hours = int(input("Duration in hours: "))
    language_required = input("Language Required: ")
    certification_offered = input("Certification Offered? (y/n): ")
    certification_offered = True if certification_offered.lower() == 'y' else False

    cur.execute("""
        INSERT INTO opportunities (ngo_id,title,description,required_skills,cause_type,city,urgency_level,importance_level,shift_type,duration_hours,language_required,certification_offered)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (ngo_id,title,description,required_skills,cause_type,city,urgency_level,importance_level,shift_type,duration_hours,language_required,certification_offered))

    conn.commit()
    print(f"Opportunity '{title}' added successfully!\n")

# ----------------------------
# 6️⃣ Menu Loop
# ----------------------------
def main():
    while True:
        print("\n--- Volunteer Database Menu ---")
        print("1. Add Student")
        print("2. Add NGO")
        print("3. Add Opportunity")
        print("4. Exit")
        choice = input("Choose an option (1-4): ")

        if choice == '1':
            add_student()
        elif choice == '2':
            add_ngo()
        elif choice == '3':
            add_opportunity()
        elif choice == '4':
            break
        else:
            print("Invalid choice! Try again.")

    cur.close()
    conn.close()
    print("Goodbye!")

# ----------------------------
# Run the script
# ----------------------------
if __name__ == "__main__":
    main()
