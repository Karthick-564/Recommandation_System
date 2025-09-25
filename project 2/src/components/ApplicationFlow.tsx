import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, MapPin, Clock, Briefcase, Star, 
  CheckCircle, Send, Heart, User
} from 'lucide-react';
import { useData } from '../context/DataContext';

const ApplicationFlow: React.FC = () => {
  const { opportunityId } = useParams<{ opportunityId: string }>();
  const navigate = useNavigate();
  const { opportunities, students, currentUser, applyToOpportunity } = useData();
  
  const [opportunity, setOpportunity] = useState(opportunities.find(opp => opp.id === opportunityId));
  const [student, setStudent] = useState(students.find(s => s.id === currentUser?.id));
  const [applicationText, setApplicationText] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!currentUser || currentUser.type !== 'student') {
      navigate('/');
      return;
    }

    const foundOpportunity = opportunities.find(opp => opp.id === opportunityId);
    const foundStudent = students.find(s => s.id === currentUser.id);
    
    if (!foundOpportunity) {
      navigate('/student/dashboard');
      return;
    }

    setOpportunity(foundOpportunity);
    setStudent(foundStudent);
  }, [opportunityId, opportunities, students, currentUser, navigate]);

  const calculateMatchScore = (): number => {
    if (!student || !opportunity) return 0;

    let score = 0;

    // Skills match (40% weight)
    const skillsIntersection = student.skills.filter(skill => 
      opportunity.requiredSkills.some(reqSkill => 
        reqSkill.toLowerCase().includes(skill.toLowerCase()) ||
        skill.toLowerCase().includes(reqSkill.toLowerCase())
      )
    );
    score += (skillsIntersection.length / opportunity.requiredSkills.length) * 40;

    // Interests match (30% weight)
    const interestsIntersection = student.interests.filter(interest =>
      opportunity.interests.some(oppInterest =>
        oppInterest.toLowerCase().includes(interest.toLowerCase()) ||
        interest.toLowerCase().includes(oppInterest.toLowerCase())
      )
    );
    score += (interestsIntersection.length / opportunity.interests.length) * 30;

    // Location match (15% weight)
    if (opportunity.workType === 'remote' || 
        student.location.toLowerCase().includes(opportunity.location.toLowerCase()) ||
        opportunity.location.toLowerCase().includes(student.location.toLowerCase())) {
      score += 15;
    }

    // Work type preference (10% weight)
    if (student.availability.workType === opportunity.workType || 
        student.availability.workType === 'hybrid') {
      score += 10;
    }

    // Time commitment compatibility (5% weight)
    if (opportunity.timeCommitment <= student.availability.hoursPerWeek) {
      score += 5;
    }

    return Math.min(Math.round(score), 100);
  };

  const handleSubmitApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!student || !opportunity) return;

    setIsLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    applyToOpportunity(student.id, opportunity.id);
    setSubmitted(true);
    setIsLoading(false);
  };

  if (!student || !opportunity) return null;

  const matchScore = calculateMatchScore();

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center px-4">
        <motion.div
          className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2, type: "spring" }}
          >
            <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          </motion.div>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Application Submitted!</h2>
          <p className="text-gray-600 mb-6">
            Your application for <strong>{opportunity.title}</strong> at <strong>{opportunity.ngoName}</strong> has been submitted successfully.
          </p>
          
          <div className="space-y-3">
            <Link
              to="/student/dashboard"
              className="block w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all font-medium"
            >
              Back to Dashboard
            </Link>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div 
          className="mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Link 
            to="/student/dashboard" 
            className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-4"
          >
            <ArrowLeft className="h-5 w-5 mr-2" />
            Back to Dashboard
          </Link>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Opportunity Details */}
          <motion.div
            className="lg:col-span-2 space-y-6"
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <div className="flex items-center space-x-3 mb-4">
                <h1 className="text-3xl font-bold text-gray-900">{opportunity.title}</h1>
                <div className="flex items-center space-x-1">
                  <Star className="h-5 w-5 text-yellow-500 fill-current" />
                  <span className="text-lg font-medium text-gray-700">{matchScore}% Match</span>
                </div>
              </div>
              
              <p className="text-xl text-blue-600 font-medium mb-4">{opportunity.ngoName}</p>
              
              <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-6">
                <div className="flex items-center space-x-1">
                  <MapPin className="h-4 w-4" />
                  <span>{opportunity.location}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="h-4 w-4" />
                  <span>{opportunity.timeCommitment}h/week</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Briefcase className="h-4 w-4" />
                  <span className="capitalize">{opportunity.workType}</span>
                </div>
              </div>

              <div className="prose max-w-none">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">About This Opportunity</h3>
                <p className="text-gray-700 leading-relaxed mb-6">{opportunity.description}</p>
              </div>

              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Required Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {opportunity.requiredSkills.map((skill: string) => (
                    <span
                      key={skill}
                      className={`px-3 py-1 text-sm rounded-full ${
                        student.skills.includes(skill) 
                          ? 'bg-green-100 text-green-700 font-medium border border-green-200' 
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {skill}
                      {student.skills.includes(skill) && ' ✓'}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Focus Areas</h3>
                <div className="flex flex-wrap gap-2">
                  {opportunity.interests.map((interest: string) => (
                    <span
                      key={interest}
                      className={`px-3 py-1 text-sm rounded-full ${
                        student.interests.includes(interest) 
                          ? 'bg-purple-100 text-purple-700 font-medium border border-purple-200' 
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {interest}
                      {student.interests.includes(interest) && ' ✓'}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          {/* Application Form */}
          <motion.div
            className="space-y-6"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            {/* Match Score Card */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <div className="text-center mb-4">
                <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full text-xl font-bold ${
                  matchScore >= 80 ? 'bg-green-100 text-green-700' :
                  matchScore >= 60 ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {matchScore}%
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mt-2">
                  {matchScore >= 80 ? 'Excellent Match' :
                   matchScore >= 60 ? 'Good Match' : 'Fair Match'}
                </h3>
                <p className="text-sm text-gray-600">Based on your profile</p>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Skills Match:</span>
                  <span className="font-medium">
                    {student.skills.filter(skill => 
                      opportunity.requiredSkills.some(reqSkill => 
                        reqSkill.toLowerCase().includes(skill.toLowerCase()) ||
                        skill.toLowerCase().includes(reqSkill.toLowerCase())
                      )
                    ).length}/{opportunity.requiredSkills.length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Interest Alignment:</span>
                  <span className="font-medium">
                    {student.interests.filter(interest =>
                      opportunity.interests.some(oppInterest =>
                        oppInterest.toLowerCase().includes(interest.toLowerCase()) ||
                        interest.toLowerCase().includes(oppInterest.toLowerCase())
                      )
                    ).length}/{opportunity.interests.length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Availability:</span>
                  <span className="font-medium">
                    {opportunity.timeCommitment <= student.availability.hoursPerWeek ? '✓' : '✗'}
                  </span>
                </div>
              </div>
            </div>

            {/* Application Form */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <User className="h-5 w-5 mr-2 text-blue-600" />
                Your Application
              </h3>
              
              <form onSubmit={handleSubmitApplication} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Why are you interested in this opportunity?
                  </label>
                  <textarea
                    required
                    rows={6}
                    value={applicationText}
                    onChange={(e) => setApplicationText(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
                    placeholder="Tell us about your motivation, relevant experience, and what you hope to contribute..."
                  />
                </div>

                <div className="bg-blue-50 rounded-lg p-4">
                  <h4 className="font-medium text-blue-900 mb-2">Your Profile Summary</h4>
                  <div className="text-sm text-blue-800 space-y-1">
                    <p><strong>Location:</strong> {student.location}</p>
                    <p><strong>Availability:</strong> {student.availability.hoursPerWeek}h/week, {student.availability.workType}</p>
                    <p><strong>Major:</strong> {student.academicMajor}</p>
                    <p><strong>Top Skills:</strong> {student.skills.slice(0, 3).join(', ')}</p>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-purple-700 transition-all duration-300 flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
                >
                  {isLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <>
                      <Send className="h-5 w-5" />
                      <span>Submit Application</span>
                    </>
                  )}
                </button>
              </form>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default ApplicationFlow;