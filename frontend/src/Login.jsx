//======================================================================
//======================================================================
// 로그인
//======================================================================
//======================================================================
import React, { useRef, useState } from 'react';
import { loginUser } from './api'; 
import { useNavigate, Link } from 'react-router-dom'; 
import './LoginPage.css';

function Login() {
  const [sid, setSid] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitting = useRef(false);
  
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Block repeated clicks/Enter immediately, before React updates the button.
    if (submitting.current) return;
    submitting.current = true;
    setIsSubmitting(true);

    try {
      await loginUser(sid, password);
    } catch (error) {
      if (error.response && (error.response.status === 401 || error.response.status === 400)) {
        alert('학번 또는 비밀번호가 일치하지 않습니다.');
      } else if (error.response && error.response.status === 429) {
        alert('로그인 시도가 너무 잦습니다. 잠시 후 다시 시도해주세요.');
      } else {
        alert('로그인 중 오류가 발생했습니다.');
      }
      setPassword('');
      submitting.current = false;
      setIsSubmitting(false);
      return;
    }

    // Keep submissions blocked until navigation replaces this successful form.
    alert('로그인에 성공했습니다!');
    navigate('/');
  };

  return (
    <main className="main-content login-page">
      <br /><br /><h1>로그인</h1>
      
      <div className="info-section">
        <h2>회원 로그인</h2>

        <form onSubmit={handleSubmit} className="login-form" aria-busy={isSubmitting}>
          <div className="form-group">
            <label htmlFor="sid-input">학번</label>
            <input 
              type="text" id="sid-input" value={sid}
              onChange={(e) => setSid(e.target.value)} required autoFocus disabled={isSubmitting}
            />
          </div>
          <div className="form-group">
            <label htmlFor="password-input">비밀번호</label>
            <input 
              type="password" id="password-input" value={password}
              onChange={(e) => setPassword(e.target.value)} required disabled={isSubmitting}
            />
          </div>
          <button type="submit" className="login-submit-button" disabled={isSubmitting}>
            {isSubmitting ? '로그인 중...' : '로그인'}
          </button>
        </form>
        
        <p style={{ marginTop: '20px', textAlign: 'center' }}>
        계정이 없으신가요? <Link to="/register">회원가입</Link>
        </p>
      </div>
    </main>
  );
}

export default Login;