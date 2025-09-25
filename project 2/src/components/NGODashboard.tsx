import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Building, Heart, Plus, Users, Eye, Clock, 
  MapPin, Briefcase, LogOut, Star, Mail
} from 'lucide-react';
import { useData } from '../context/DataContext';

const NGODashboard: React.FC = () => {
  const navigate = useNavigate();
  const { ngos, opportunities, students, currentUser, setCurrentUser, addOpportunity } = useData();
  const [ngo, setNgo] = useState(ngos.find(n => n.id === currentUser?.id));
  const [ngoOpportunities, setNgoOpportunities] = useState<any[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  
  const [newOpportunity, setNewOpportunity] = useState({
    title: '',
    description: '',
    requiredSkills: [] as string[],
    interests: [] as string[],
    location: '',
    workType: 'hybrid' as 'remote' | 'onsite' | 'hybrid',
    timeCommitment: 5
  });

  const skillOptions = [
    'JavaScript', 'Python', 'React', 'Data Analysis', 'Public Speaking', 
    'Event Planning', 'Graphic Design', 'Writing', 'Social Media', 'Teaching',
    'Project Management', 'Research', 'Marketing', 'Photography', 'Video Editing'
  ];

  const interestOptions = [
    'Education', 'Technology', 'Environment', 'Healthcare', 'Animal Welfare',
    'Human Rights', 'Poverty Alleviation', 'Youth Development', 'Community Development'
  ];

  useEffect(() => {
    if (!currentUser || currentUser.type !== 'ngo') {
      navigate('/');
      return;
    }

    const foundNgo = ngos.find(n => n.id === currentUser.id);
    if (foundNgo) {
      setNgo(foundNgo);
      const ngoOpps = opportunities.filter(opp => opp.ngoName === foundNgo.name);
      setNgoOpportunities(ngoOpps);
    }
  }, [currentUser, ngos, opportunities, navigate]);

  const handleLogout = () => {
    setCurrentUser(null);
    navigate('/');
  };

  const handleSkillToggle = (skill: string) => {
    setNewOpportunity(prev => ({
      ...prev,
      requiredSkills: prev.requiredSkills.includes(skill)
        ? prev.requiredSkills.filter(s => s !== skill)
        : [...prev.requiredSkills, skill]
    }));
  };

  const handleInterestToggle = (interest: string) => {
    setNewOpportunity(prev => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter(i => i !== interest)
        : [...prev.interests, interest]
    }));
  };

  const handleCreateOpportunity = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ngo) return;

    const opportunity = {
      id: Date.now().toString(),
      title: newOpportunity.title,
      ngoName: ngo.name,
      description: newOpportunity.description,
      requiredSkills: newOpportunity.requiredSkills,
      interests: newOpportunity.interests,
      location: newOpportunity.location,
      workType: newOpportunity.workType,
      timeCommitment: newOpportunity.timeCommitment,
      applicants: []
    };

    addOpportunity(opportunity);
    setShowCreateForm(false);
    setNewOpportunity({
      title: '',
      description: '',
      requiredSkills: [],
      interests: [],
      location: '',
      workType: 'hybrid',
      timeCommitment: 5
    });
  };

  const getMatchedStudents = (opportunityId: string) => {
    const opportunity = opportunities.find(opp => opp.id === opportunityId);
    if (!opportunity) return [];

    return opportunity.applicants.map(applicant => {
      const student = students.find(s => s.id === applicant.studentId);
      return { ...applicant, student };
    });
  };

  if (!ngo) return null;

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
              <span className="text-gray-700">Welcome, {ngo.name}</span>
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
            <div className="flex justify-between items-start">
              <div>
                <h1 className="text-3xl font-bold mb-4">NGO Dashboard</h1>
                <p className="text-blue-100 mb-6">{ngo.description}</p>
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">{ngoOpportunities.length}</div>
                    <div className="text-sm text-blue-100">Active Opportunities</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">
                      {ngoOpportunities.reduce((acc, opp) => acc + opp.applicants.length, 0)}
                    </div>
                    <div className="text-sm text-blue-100">Total Applications</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{ngo.focus.length}</div>
                    <div className="text-sm text-blue-100">Focus Areas</div>
                  </div>
                </div>
              </div>
              
              <button
                onClick={() => setShowCreateForm(true)}
                className="bg-white/20 hover:bg-white/30 text-white px-6 py-3 rounded-xl transition-colors font-medium flex items-center space-x-2"
              >
                <Plus className="h-5 w-5" />
                <span>Post Opportunity</span>
              </button>
            </div>
          </div>
        </motion.div>

        {/* Create Opportunity Modal */}
        {showCreateForm && (
          <motion.div
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="bg-white rounded-2xl shadow-2xl p-8 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Create New Opportunity</h2>
              
              <form onSubmit={handleCreateOpportunity} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Opportunity Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={newOpportunity.title}
                    onChange={(e) => setNewOpportunity(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="e.g., Youth Coding Mentor"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description *
                  </label>
                  <textarea
                    required
                    rows={4}
                    value={newOpportunity.description}
                    onChange={(e) => setNewOpportunity(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="Describe the volunteer opportunity..."
                  />
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Location *
                    </label>
                    <input
                      type="text"
                      required
                      value={newOpportunity.location}
                      onChange={(e) => setNewOpportunity(prev => ({ ...prev, location: e.target.value }))}
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      placeholder="City, State or Remote"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Work Type
                    </label>
                    <select
                      value={newOpportunity.workType}
                      onChange={(e) => setNewOpportunity(prev => ({ ...prev, workType: e.target.value as any }))}
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    >
                      <option value="remote">Remote</option>
                      <option value="onsite">On-site</option>
                      <option value="hybrid">Hybrid</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Time Commitment (hours/week)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="40"
                    value={newOpportunity.timeCommitment}
                    onChange={(e) => setNewOpportunity(prev => ({ ...prev, timeCommitment: parseInt(e.target.value) }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Required Skills
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {skillOptions.map(skill => (
                      <button
                        key={skill}
                        type="button"
                        onClick={() => handleSkillToggle(skill)}
                        className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                          newOpportunity.requiredSkills.includes(skill)
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {skill}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Related Interests
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {interestOptions.map(interest => (
                      <button
                        key={interest}
                        type="button"
                        onClick={() => handleInterestToggle(interest)}
                        className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                          newOpportunity.interests.includes(interest)
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {interest}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex space-x-4">
                  <button
                    type="button"
                    onClick={() => setShowCreateForm(false)}
                    className="flex-1 px-6 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all font-medium"
                  >
                    Create Opportunity
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}

        {/* Opportunities List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <Building className="h-6 w-6 mr-2 text-blue-600" />
              Your Opportunities
            </h2>
          </div>

          <div className="grid gap-6">
            {ngoOpportunities.map((opportunity, index) => {
              const matchedStudents = getMatchedStudents(opportunity.id);
              
              return (
                <motion.div
                  key={opportunity.id}
                  className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition-all duration-300 border border-gray-100"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                >
                  <div className="flex flex-col lg:flex-row lg:items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="text-xl font-semibold text-gray-900 mb-2">{opportunity.title}</h3>
                      <p className="text-gray-600 mb-4">{opportunity.description}</p>
                      
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
                        <div className="flex items-center space-x-1">
                          <Users className="h-4 w-4" />
                          <span>{matchedStudents.length} applicants</span>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2 mb-4">
                        {opportunity.requiredSkills.map((skill: string) => (
                          <span key={skill} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Applicants */}
                  {matchedStudents.length > 0 && (
                    <div className="border-t border-gray-200 pt-4">
                      <h4 className="font-medium text-gray-900 mb-3">Recent Applicants</h4>
                      <div className="space-y-3">
                        {matchedStudents.slice(0, 3).map((applicant, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center space-x-3">
                              <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                                {applicant.studentName.charAt(0)}
                              </div>
                              <div>
                                <p className="font-medium text-gray-900">{applicant.studentName}</p>
                                <p className="text-sm text-gray-600">
                                  Applied {new Date(applicant.appliedAt).toLocaleDateString()}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                applicant.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                                applicant.status === 'accepted' ? 'bg-green-100 text-green-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {applicant.status}
                              </span>
                              <button className="p-2 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors">
                                <Mail className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                        {matchedStudents.length > 3 && (
                          <p className="text-sm text-gray-500 text-center">
                            +{matchedStudents.length - 3} more applicants
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>

          {ngoOpportunities.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-500 mb-4">
                <Building className="h-12 w-12 mx-auto opacity-50" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No opportunities posted yet</h3>
              <p className="text-gray-600 mb-4">Create your first volunteer opportunity to start connecting with students</p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all font-medium"
              >
                Post Your First Opportunity
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default NGODashboard;