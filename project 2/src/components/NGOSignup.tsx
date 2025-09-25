import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Building, Mail, FileText, Tag, ArrowLeft, ArrowRight } from 'lucide-react';
import { useData } from '../context/DataContext';

const NGOSignup: React.FC = () => {
  const navigate = useNavigate();
  const { addNGO, setCurrentUser } = useData();
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    description: '',
    focus: [] as string[]
  });

  const focusAreas = [
    'Education', 'Technology', 'Environment', 'Healthcare', 'Animal Welfare',
    'Human Rights', 'Poverty Alleviation', 'Youth Development', 'Elder Care',
    'Arts & Culture', 'Community Development', 'Mental Health', 'Food Security',
    'Climate Action', 'Social Justice', 'Disaster Relief', 'International Development'
  ];

  const handleFocusToggle = (area: string) => {
    setFormData(prev => ({
      ...prev,
      focus: prev.focus.includes(area)
        ? prev.focus.filter(f => f !== area)
        : [...prev.focus, area]
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const ngo = {
      id: Date.now().toString(),
      name: formData.name,
      email: formData.email,
      description: formData.description,
      focus: formData.focus,
      opportunities: []
    };

    addNGO(ngo);
    setCurrentUser({ id: ngo.id, type: 'ngo' });
    navigate('/ngo/dashboard');
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
            <h1 className="text-4xl font-bold text-gray-900 mb-4">Register Your NGO</h1>
            <p className="text-xl text-gray-600">Connect with passionate students ready to make a difference</p>
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
            {/* Organization Information */}
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
                <Building className="h-6 w-6 mr-3 text-blue-600" />
                Organization Information
              </h2>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Organization Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="Your organization name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Contact Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="contact@yourorg.org"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Organization Description *
                </label>
                <textarea
                  required
                  rows={4}
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="Tell us about your organization's mission and impact..."
                />
              </div>
            </div>

            {/* Focus Areas */}
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-900 flex items-center">
                <Tag className="h-6 w-6 mr-3 text-blue-600" />
                Focus Areas
              </h2>
              <p className="text-gray-600">Select the areas your organization works in</p>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {focusAreas.map(area => (
                  <button
                    key={area}
                    type="button"
                    onClick={() => handleFocusToggle(area)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      formData.focus.includes(area)
                        ? 'bg-blue-600 text-white shadow-md transform scale-105'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {area}
                  </button>
                ))}
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-6 border-t border-gray-200">
              <button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 rounded-xl font-semibold text-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-300 flex items-center justify-center space-x-2 transform hover:scale-105"
              >
                <span>Create NGO Profile</span>
                <ArrowRight className="h-5 w-5" />
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
};

export default NGOSignup;