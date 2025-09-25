import React, { createContext, useContext, useState, useEffect } from 'react';

export interface Student {
  id: string;
  name: string;
  email: string;
  skills: string[];
  interests: string[];
  location: string;
  availability: {
    hoursPerWeek: number;
    preferredDays: string[];
    workType: 'remote' | 'onsite' | 'hybrid';
  };
  academicMajor: string;
  applications: string[];
}

export interface Opportunity {
  id: string;
  title: string;
  ngoName: string;
  description: string;
  requiredSkills: string[];
  interests: string[];
  location: string;
  workType: 'remote' | 'onsite' | 'hybrid';
  timeCommitment: number;
  matchScore?: number;
  applicants: {
    studentId: string;
    studentName: string;
    appliedAt: Date;
    status: 'pending' | 'accepted' | 'rejected';
  }[];
}

export interface NGO {
  id: string;
  name: string;
  email: string;
  description: string;
  focus: string[];
  opportunities: string[];
}

interface DataContextType {
  students: Student[];
  opportunities: Opportunity[];
  ngos: NGO[];
  currentUser: { id: string; type: 'student' | 'ngo' } | null;
  addStudent: (student: Student) => void;
  addNGO: (ngo: NGO) => void;
  addOpportunity: (opportunity: Opportunity) => void;
  applyToOpportunity: (studentId: string, opportunityId: string) => void;
  setCurrentUser: (user: { id: string; type: 'student' | 'ngo' } | null) => void;
  getRecommendations: (studentId: string) => Opportunity[];
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const useData = () => {
  const context = useContext(DataContext);
  if (!context) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
};

// Sample data for demo
const sampleStudents: Student[] = [
  {
    id: '1',
    name: 'Alex Chen',
    email: 'alex.chen@university.edu',
    skills: ['Python', 'JavaScript', 'React', 'Data Analysis', 'Public Speaking'],
    interests: ['Education', 'Technology', 'Youth Development'],
    location: 'San Francisco, CA',
    availability: {
      hoursPerWeek: 10,
      preferredDays: ['Saturday', 'Sunday'],
      workType: 'hybrid'
    },
    academicMajor: 'Computer Science',
    applications: []
  }
];

const sampleNGOs: NGO[] = [
  {
    id: '1',
    name: 'TechForGood',
    email: 'contact@techforgood.org',
    description: 'Bridging the digital divide through technology education',
    focus: ['Education', 'Technology', 'Digital Literacy'],
    opportunities: ['1']
  },
  {
    id: '2',
    name: 'Green Future Initiative',
    email: 'info@greenfuture.org',
    description: 'Environmental conservation and sustainability programs',
    focus: ['Environment', 'Sustainability', 'Climate Action'],
    opportunities: ['2']
  },
  {
    id: '3',
    name: 'Community Health Alliance',
    email: 'hello@healthalliance.org',
    description: 'Promoting health and wellness in underserved communities',
    focus: ['Healthcare', 'Community Development', 'Wellness'],
    opportunities: ['3']
  }
];

const sampleOpportunities: Opportunity[] = [
  {
    id: '1',
    title: 'Code Mentor for High School Students',
    ngoName: 'TechForGood',
    description: 'Mentor high school students in programming and web development. Help them build their first websites and mobile apps.',
    requiredSkills: ['JavaScript', 'Python', 'React', 'Teaching'],
    interests: ['Education', 'Technology', 'Youth Development'],
    location: 'San Francisco, CA',
    workType: 'hybrid',
    timeCommitment: 8,
    applicants: []
  },
  {
    id: '2',
    title: 'Environmental Data Analyst',
    ngoName: 'Green Future Initiative',
    description: 'Analyze environmental data to track conservation progress and create compelling visualizations for fundraising.',
    requiredSkills: ['Data Analysis', 'Python', 'Excel', 'Visualization'],
    interests: ['Environment', 'Data Science', 'Research'],
    location: 'Remote',
    workType: 'remote',
    timeCommitment: 12,
    applicants: []
  },
  {
    id: '3',
    title: 'Health Education Workshop Facilitator',
    ngoName: 'Community Health Alliance',
    description: 'Lead interactive workshops on nutrition and wellness for community members of all ages.',
    requiredSkills: ['Public Speaking', 'Health Knowledge', 'Event Planning'],
    interests: ['Healthcare', 'Community Development', 'Education'],
    location: 'Los Angeles, CA',
    workType: 'onsite',
    timeCommitment: 6,
    applicants: []
  }
];

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [students, setStudents] = useState<Student[]>(sampleStudents);
  const [opportunities, setOpportunities] = useState<Opportunity[]>(sampleOpportunities);
  const [ngos, setNGOs] = useState<NGO[]>(sampleNGOs);
  const [currentUser, setCurrentUser] = useState<{ id: string; type: 'student' | 'ngo' } | null>(null);

  // Load data from localStorage
  useEffect(() => {
    const savedStudents = localStorage.getItem('students');
    const savedOpportunities = localStorage.getItem('opportunities');
    const savedNGOs = localStorage.getItem('ngos');
    const savedCurrentUser = localStorage.getItem('currentUser');

    if (savedStudents) setStudents(JSON.parse(savedStudents));
    if (savedOpportunities) setOpportunities(JSON.parse(savedOpportunities));
    if (savedNGOs) setNGOs(JSON.parse(savedNGOs));
    if (savedCurrentUser) setCurrentUser(JSON.parse(savedCurrentUser));
  }, []);

  // Save to localStorage whenever data changes
  useEffect(() => {
    localStorage.setItem('students', JSON.stringify(students));
  }, [students]);

  useEffect(() => {
    localStorage.setItem('opportunities', JSON.stringify(opportunities));
  }, [opportunities]);

  useEffect(() => {
    localStorage.setItem('ngos', JSON.stringify(ngos));
  }, [ngos]);

  useEffect(() => {
    if (currentUser) {
      localStorage.setItem('currentUser', JSON.stringify(currentUser));
    }
  }, [currentUser]);

  const addStudent = (student: Student) => {
    setStudents(prev => [...prev, student]);
  };

  const addNGO = (ngo: NGO) => {
    setNGOs(prev => [...prev, ngo]);
  };

  const addOpportunity = (opportunity: Opportunity) => {
    setOpportunities(prev => [...prev, opportunity]);
  };

  const applyToOpportunity = (studentId: string, opportunityId: string) => {
    const student = students.find(s => s.id === studentId);
    if (!student) return;

    setOpportunities(prev => prev.map(opp => 
      opp.id === opportunityId 
        ? {
            ...opp,
            applicants: [...opp.applicants, {
              studentId,
              studentName: student.name,
              appliedAt: new Date(),
              status: 'pending' as const
            }]
          }
        : opp
    ));

    setStudents(prev => prev.map(s => 
      s.id === studentId 
        ? { ...s, applications: [...s.applications, opportunityId] }
        : s
    ));
  };

  const getRecommendations = (studentId: string): Opportunity[] => {
    const student = students.find(s => s.id === studentId);
    if (!student) return [];

    return opportunities
      .filter(opp => !student.applications.includes(opp.id))
      .map(opp => ({
        ...opp,
        matchScore: calculateMatchScore(student, opp)
      }))
      .sort((a, b) => (b.matchScore || 0) - (a.matchScore || 0));
  };

  const calculateMatchScore = (student: Student, opportunity: Opportunity): number => {
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

  const value = {
    students,
    opportunities,
    ngos,
    currentUser,
    addStudent,
    addNGO,
    addOpportunity,
    applyToOpportunity,
    setCurrentUser,
    getRecommendations
  };

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  );
};