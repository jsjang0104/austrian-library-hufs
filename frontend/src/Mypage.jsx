import React, { useEffect, useState } from 'react';
import { useAuth } from './AuthContext';
import { useNavigate } from 'react-router-dom';
import http from './api/http';
import './App.css';

function MyPage() {
  const { user, isLoggedIn } = useAuth();
  const navigate = useNavigate();
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const ROLE_MAP = {
    'UNDERGRADUATE': '학부생/졸업생',
    'GRADUATE': '대학원생',
    'PROFESSOR': '교수',
    'ADMIN': '관리자'
  };

  useEffect(() => {
    if (!isLoggedIn) {
      alert("로그인이 필요한 서비스입니다.");
      navigate('/login');
      return;
    }

    const fetchMyLoans = async () => {
      try {
        setLoading(true);
        const response = await http.get('/api/loans/');
        setLoans(response.data);
      } catch (error) {
        console.error("대출 목록 로딩 실패:", error);
      }
      setLoading(false);
    };

    fetchMyLoans();
  }, [isLoggedIn, navigate]);

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString();
  };

  const checkOverdue = (loan) => {
    if (loan.return_date) return false; 
    if (loan.overdue_days > 0) return true;
    const today = new Date();
    const due = new Date(loan.due_date);
    return today > due;
  };

  if (!isLoggedIn) return null;

  return (
    <main className="main-content info-page">
      <br /><br />
      <h1>내 서재</h1>

      <div className="info-section">
        <h2>회원 정보</h2>
        <p><strong>이름:</strong> {user?.name}</p>
        <p><strong>학번(ID):</strong> {user?.sid}</p> 
      </div>
      <div className="info-section">
        <h2>대출 현황</h2>
        {loading ? (
           <p>정보를 불러오는 중...</p>
        ) : (
          <div className="table-container">
            <table className="library-table">
              <thead>
                <tr>
                  <th>번호</th>
                  <th>도서명</th>
                  <th>대출일</th>
                  <th>반납예정일</th>
                  <th>상태</th>
                  <th>반납여부</th>
                </tr>
              </thead>
              <tbody>
                {loans && loans.length > 0 ? (
                  loans.map((loan, index) => {
                    const bookTitle = loan.book_title || loan.book?.title || "도서 정보 없음";
                    const isOverdue = checkOverdue(loan);

                    return (
                      <tr key={loan.loan_id || index}>
                        <td>{index + 1}</td>
                        <td className="text-left" style={{fontWeight: 500}}>
                            {bookTitle}
                        </td>
                        <td>{formatDate(loan.loan_date)}</td>
                        <td>{formatDate(loan.due_date)}</td>
                        
                        <td style={{ 
                          color: isOverdue ? 'red' : 'green', 
                          fontWeight: 500
                        }}>
                          {isOverdue ? '연체중' : '정상'}
                        </td>

                        <td>
                          {loan.return_date ? (
                            <span style={{color: '#999'}}>반납완료</span>
                          ) : (
                            <span style={{color: '#003366'}}>대출중</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="6" className="no-result">대출 기록이 없습니다.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}

export default MyPage;