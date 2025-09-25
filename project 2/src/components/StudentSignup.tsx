import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { User, Mail, MapPin, Clock, Briefcase, Heart, ArrowLeft, ArrowRight } from 'lucide-react';
import { useData } from '../context/DataContext';

const StudentSignup: React.FC = () => {
  const navigate = useNavigate();
  const { addStudent, setCurrentUser } = useData();
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    skills: [] as string[],
    interests: [] as string[],
    location: '',
    hoursPerWeek: 5,
    preferredDays: [] as string[],
    workType: 'hybrid' as 'remote' | 'onsite' | 'hybrid',
    academicMajor: ''
  });

  const skillOptions = [
    'JavaScript', 'Python', 'React', 'Data Analysis', 'Public Speaking', 
    'Event Planning', 'Graphic Design', 'Writing', 'Social Media', 'Teaching',
    'Project Management', 'Research', 'Marketing', 'Photography', 'Video Editing',
    'Fundraising', 'Grant Writing', 'Translation', 'Web Design', 'Mobile Development'
  ];

  const interestOptions = [
    'Education', 'Technology', 'Environment', 'Healthcare', 'Animal Welfare',
    'Human Rights', 'Poverty Alleviation', 'Youth Development', 'Elder Care',
    'Arts & Culture', 'Community Development', 'Mental Health', 'Food Security',
    'Climate Action', 'Social Justice', 'Disaster Relief', 'International Development'
  ];

  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  const handleSkillToggle = (skill: string) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.includes(skill)
        ? prev.skills.filter(s => s !== skill)
        : [...prev.skills, skill]
    }));
  };

  const handleInterestToggle = (interest: string) => {
    setFormData(prev => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter(i => i !== interest)
        : [...prev.interests, interest]
    }));
  };

  const handleDayToggle = (day: string) => {
    setFormData(prev => ({
      ...prev,
      preferredDays: prev.preferredDays.includes(day)
        ? prev.preferredDays.filter(d => d !== day)
        : [...prev.preferredDays, day]
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const student = {
      id: Date.now().toString(),
      name: formData.name,
      email: formData.email,
      skills: formData.skills,
      interests: formData.interests,
      location: formData.location,
      availability: {
        hoursPerWeek: formData.hoursPerWeek,
        preferredDays: formData.preferredDays,
        workType: formData.workType
      },
      academicMajor: formData.academicMajor,
      applications: []
    };

    addStudent(student);
    setCurrentUser({ id: student.id, type: 'student' });
    navigate('/student/dashboard');
  };

  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div 
          className="mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Link to="/" className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-4">
            <ArrowLeft className="h-5 w-5 mr-2" />
            Back to Home
          </Link>
          
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">Create Your Student Profile</h1>
            <p className="text-xl text-gray-600">Help us find the perfect volunteer opportunities for you</p>
          </div>
        </motion.div>

        {/* Form */}
        <motion.div 
          className="bg-white rounded-2xl shadow-xl p-8"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Personal Information */}
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
                <User className="h-6 w-6 mr-3 text-blue-600" />
                Personal Information
              </h2>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="Your full name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Email Address *
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="your.email@university.edu"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Location *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.location}
                    onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="City, State"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Academic Major
                  </label>
                  <input
                    type="text"
                    value={formData.academicMajor}
                    onChange={(e) => setFormData(prev => ({ ...prev, academicMajor: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="Computer Science, Psychology, etc."
                  />
                </div>
              </div>
            </div>

            {/* Skills */}
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
                <Briefcase className="h-6 w-6 mr-3 text-blue-600" />
                Your Skills
              </h2>
              <p className="text-gray-600">Select all skills that apply to you</p>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {skillOptions.map(skill => (
                  <button
                    key={skill}
                    type="button"
                    onClick={() => handleSkillToggle(skill)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      formData.skills.includes(skill)
                        ? 'bg-blue-600 text-white shadow-md transform scale-105'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {skill}
                  </button>
                ))}
              </div>
            </div>

            {/* Interests */}
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
                <Heart className="h-6 w-6 mr-3 text-blue-600" />
                Your Interests
              </h2>
              <p className="text-gray-600">What causes are you passionate about?</p>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {interestOptions.map(interest => (
                  <button
                    key={interest}
                    type="button"
                    onClick={() => handleInterestToggle(interest)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      formData.interests.includes(interest)
                        ? 'bg-purple-600 text-white shadow-md transform scale-105'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {interest}
                  </button>
                ))}
              </div>
            </div>

            {/* Availability */}
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
                <Clock className="h-6 w-6 mr-3 text-blue-600" />
                Availability
              </h2>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hours per week you can volunteer
                  </label>
                  <select
                    value={formData.hoursPerWeek}
                    onChange={(e) => setFormData(prev => ({ ...prev, hoursPerWeek: parseInt(e.target.value) }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  >
                    <option value={2}>2-3 hours</option>
                    <option value={5}>4-6 hours</option>
                    <option value={8}>7-10 hours</option>
                    <option value={12}>10+ hours</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Work Type Preference
                  </label>
                  <select
                    value={formData.workType}
                    onChange={(e) => setFormData(prev => ({ ...prev, workType: e.target.value as any }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  >
                    <option value="remote">Remote only</option>
                    <option value="onsite">On-site only</option>
                    <option value="hybrid">Either remote or on-site</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Preferred days of the week
                </label>
                <div className="grid grid-cols-4 sm:grid-cols-7 gap-3">
                  {daysOfWeek.map(day => (
                    <button
                      key={day}
                      type="button"
                      onClick={() => handleDayToggle(day)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                        formData.preferredDays.includes(day)
                          ? 'bg-green-600 text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {day.slice(0, 3)}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-6 border-t border-gray-200">
              <button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 rounded-xl font-semibold text-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-300 flex items-center justify-center space-x-2 transform hover:scale-105"
              >
                <span>Create Profile & Find Opportunities</span>
                <ArrowRight className="h-5 w-5" />
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
};

export default StudentSignup;