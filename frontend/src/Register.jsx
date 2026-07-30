//======================================================================
//======================================================================
// 회원가입 
//======================================================================
//======================================================================
import React, { useState } from 'react';
import { registerUser } from './api'; 
import { useNavigate, Link } from 'react-router-dom'; 
import './RegisterPage.css';

function Register() {
  const [sid, setSid] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('UNDERGRADUATE'); 
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault(); 

    if (password !== passwordConfirm) {
      alert('비밀번호가 일치하지 않습니다.'); 
      return; 
    }

    const userData = { sid, name, email, password, role };

    try {
      const response = await registerUser(userData);
      const result = response.data || response;
      console.log('회원가입 성공 데이터:', result);
      const successName = result?.name || name; 
      alert(`${successName}님, 회원가입이 완료되었습니다. 로그인해주세요.`);
      navigate('/login');

    } catch (error) {
      console.error('회원가입 실패:', error.response ? error.response.data : error.message);
      
      if (error.response && error.response.status === 400) {
        const errorData = error.response.data;
        let errorMessage = '회원가입에 실패했습니다.\n';
        if (errorData.sid) errorMessage += `학번: ${errorData.sid.join(' ')}\n`;
        if (errorData.email) errorMessage += `이메일: ${errorData.email.join(' ')}\n`;
        
        alert(errorMessage);
      } else {
        alert('회원가입 중 오류가 발생했습니다. (서버 오류 등)');
      }
    }
  };

  return (
    <main className="main-content register-page">
      <br /><br /><h1>회원가입</h1>
      
      <div className="info-section">
        <h2>회원 정보 입력</h2>
        
        <form onSubmit={handleSubmit} className="register-form">
          <div className="form-group">
            <label htmlFor="sid-input">학번</label>
            <input 
              type="text" id="sid-input" value={sid}
              onChange={(e) => setSid(e.target.value)} required autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="name-input">이름</label>
            <input 
              type="text" id="name-input" value={name}
              onChange={(e) => setName(e.target.value)} required
            />
          </div>

          <div className="form-group">
            <label htmlFor="role-select">신분</label>
            <select 
              id="role-select"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                backgroundColor: '#fff',
                fontSize: '1rem',
                color: '#333'
              }}
            >
              <option value="UNDERGRADUATE">학부생/졸업생</option>
              <option value="GRADUATE">대학원생</option>
              <option value="PROFESSOR">교수</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="email-input">이메일</label>
            <input 
              type="email" id="email-input" value={email}
              onChange={(e) => setEmail(e.target.value)} required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password-input">비밀번호</label>
            <input 
              type="password" id="password-input" value={password}
              onChange={(e) => setPassword(e.target.value)} required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password-confirm-input">비밀번호 확인</label>
            <input 
              type="password" id="password-confirm-input" value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)} required
            />
          </div>

          <button type="submit" className="register-submit-button">
            가입하기
          </button>
        </form>
        
        <p style={{ marginTop: '20px', textAlign: 'center' }}>
        이미 계정이 있으신가요? <Link to="/login">로그인</Link>
        </p>
      </div>
    </main>
  );
}

export default Register;