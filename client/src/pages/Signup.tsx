import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { request } from '../services/api';

const Signup: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await request('/users/signup', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      navigate('/login');
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="card" style={{ maxWidth: '400px', margin: '40px auto' }}>
      <h2>회원가입</h2>
      {error && <div className="error mb-1">{error}</div>}
      <form onSubmit={handleSubmit} className="flex-col gap-2">
        <div>
          <label>이메일</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
        </div>
        <div>
          <label>비밀번호</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
        </div>
        <button type="submit">회원가입</button>
      </form>
    </div>
  );
};

export default Signup;
