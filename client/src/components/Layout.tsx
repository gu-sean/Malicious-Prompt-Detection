import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Layout: React.FC = () => {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="container">
      <header className="flex gap-2 mb-2" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '16px', alignItems: 'center' }}>
        <div style={{ fontWeight: 'bold', fontSize: '18px' }}>악성 프롬프트 탐지 시스템</div>
        <nav className="flex gap-2" style={{ marginLeft: 'auto' }}>
          <Link to="/">홈 (테스트)</Link>
          {isAuthenticated ? (
            <>
              <Link to="/dashboard">대시보드</Link>
              <Link to="/keys">API 키 관리</Link>
              <Link to="/logs">탐지 로그</Link>
              <Link to="/docs">API 문서</Link>
              <button onClick={handleLogout} style={{ padding: '4px 8px' }}>로그아웃</button>
            </>
          ) : (
            <>
              <Link to="/login">로그인</Link>
              <Link to="/signup">회원가입</Link>
            </>
          )}
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
