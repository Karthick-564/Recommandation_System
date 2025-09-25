import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  User, Heart, MapPin, Clock, Briefcase, Star, 
  ExternalLink, Filter, Search, LogOut, Zap 
} from 'lucide-react';
import { useData } from '../context/DataContext';

const StudentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { students, currentUser, getRecommendations, setCurrentUser } = useData();
  const [student, setStudent] = useState(students.find(s => s.id === currentUser?.id));
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (!currentUser || currentUser.type !== 'student') {
      navigate('/');
      return;
    }

    const foundStudent = students.find(s => s.id === currentUser.id);
    if (foundStudent) {
      setStudent(foundStudent);
      const recs = getRecommendations(foundStudent.id);
      setRecommendations(recs);
    }
  }, [currentUser, students, navigate, getRecommendations]);

  const handleLogout = () => {
    setCurrentUser(null);
    navigate('/');
  };

  const filteredRecommendations = recommendations.filter(opp =>
    opp.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    opp.ngoName.toLowerCase().includes(searchTerm.toLowerCase()) ||
    opp.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!student) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center space-x-2">
              <Heart className="h-8 w-8 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">VolunteerAI</span>
            </Link>
            
            <div className="flex items-center space-x-4">
              <span className="text-gray-700">Welcome, {student.name.split(' ')[0]}</span>
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <motion.div 
          className="mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-2xl p-8">
            <h1 className="text-3xl font-bold mb-4">Your Personalized Dashboard</h1>
            <p className="text-blue-100 mb-6">
              Based on your profile, we've found {recommendations.length} opportunities that match your skills and interests.
            </p>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">{student.skills.length}</div>
                <div className="text-sm text-blue-100">Skills Listed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{student.interests.length}</div>
                <div className="text-sm text-blue-100">Interests</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{student.applications.length}</div>
                <div className="text-sm text-blue-100">Applications</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{recommendations.length}</div>
                <div className="text-sm text-blue-100">Matches</div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Profile Overview */}
        <motion.div 
          className="mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <User className="h-5 w-5 mr-2 text-blue-600" />
              Your Profile
            </h2>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex items-center space-x-2">
                <MapPin className="h-4 w-4 text-gray-500" />
                <span className="text-sm text-gray-700">{student.location}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-gray-500" />
                <span className="text-sm text-gray-700">{student.availability.hoursPerWeek}h/week</span>
              </div>
              <div className="flex items-center space-x-2">
                <Briefcase className="h-4 w-4 text-gray-500" />
                <span className="text-sm text-gray-700">{student.availability.workType}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Heart className="h-4 w-4 text-gray-500" />
                <span className="text-sm text-gray-700">{student.academicMajor}</span>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {student.skills.slice(0, 5).map(skill => (
                <span key={skill} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                  {skill}
                </span>
              ))}
              {student.skills.length > 5 && (
                <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                  +{student.skills.length - 5} more
                </span>
              )}
            </div>
          </div>
        </motion.div>

        {/* Search and Filters */}
        <motion.div 
          className="mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search opportunities..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="px-6 py-3 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2"
            >
              <Filter className="h-5 w-5" />
              <span>Filters</span>
            </button>
          </div>
        </motion.div>

        {/* Recommendations */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <Zap className="h-6 w-6 mr-2 text-yellow-500" />
              Recommended for You
            </h2>
            <div className="text-sm text-gray-500">
              {filteredRecommendations.length} opportunities found
            </div>
          </div>

          <div className="grid gap-6">
            {filteredRecommendations.map((opportunity, index) => (
              <motion.div
                key={opportunity.id}
                className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition-all duration-300 border border-gray-100"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-xl font-semibold text-gray-900">{opportunity.title}</h3>
                      <div className="flex items-center space-x-1">
                        <Star className="h-4 w-4 text-yellow-500 fill-current" />
                        <span className="text-sm font-medium text-gray-700">{opportunity.matchScore}% Match</span>
                      </div>
                    </div>
                    <p className="text-blue-600 font-medium mb-2">{opportunity.ngoName}</p>
                    <p className="text-gray-600 line-clamp-2">{opportunity.description}</p>
                  </div>
                  
                  <div className="flex flex-col items-end space-y-2 mt-4 lg:mt-0">
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                      opportunity.matchScore >= 80 ? 'bg-green-100 text-green-700' :
                      opportunity.matchScore >= 60 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {opportunity.matchScore >= 80 ? 'Excellent Match' :
                       opportunity.matchScore >= 60 ? 'Good Match' : 'Fair Match'}
                    </div>
                    
                    <Link
                      to={`/apply/${opportunity.id}`}
                      className="inline-flex items-center space-x-2 px-6 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-300 font-medium transform hover:scale-105"
                    >
                      <span>Apply Now</span>
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </div>
                </div>

                <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-4">
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

                <div className="flex flex-wrap gap-2">
                  {opportunity.requiredSkills.slice(0, 4).map((skill: string) => (
                    <span key={skill} className={`px-2 py-1 text-xs rounded-full ${
                      student.skills.includes(skill) 
                        ? 'bg-green-100 text-green-700 font-medium' 
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      {skill}
                      {student.skills.includes(skill) && ' ✓'}
                    </span>
                  ))}
                  {opportunity.requiredSkills.length > 4 && (
                    <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                      +{opportunity.requiredSkills.length - 4} more
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          {filteredRecommendations.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-500 mb-4">
                <Search className="h-12 w-12 mx-auto opacity-50" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No opportunities found</h3>
              <p className="text-gray-600">Try adjusting your search terms or filters</p>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default StudentDashboard;